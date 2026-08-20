"""WS /api/chat — Tutor Chat 에이전트 실시간 대화 엔드포인트.

연결: ws://.../api/chat?result_id=...&user_identifier=...
  - result_id: 대화 컨텍스트로 쓸 채점 결과 (ChatSession은 result_id 기준 1:1 — ERD.md)
  - user_identifier: 세션 소유권 검사용 (인증 아님, 컴포넌트 설계서 7절)

메시지 프로토콜 (JSON):
  서버 -> 클라이언트: {"type": "ready", "history": [...]}                (연결 직후, 과거 대화 이력)
  클라이언트 -> 서버:  평문 텍스트 (질문 메시지)
  서버 -> 클라이언트: {"type": "chunk", "content": "..."}                (스트리밍 조각, 여러 번)
  서버 -> 클라이언트: {"type": "done"}                                   (스트리밍 끝, 정상 완료)
  서버 -> 클라이언트: {"type": "blocked", "reason": "..."}               (입력 가드레일 차단 — LLM 호출 자체를 안 함)
  서버 -> 클라이언트: {"type": "error", "detail": "..."}                 (오류 시, 연결은 유지)

result_id는 연결 시점에 서버가 검증한 값만 이후 모든 메시지 처리에 쓴다 — 채팅 중 사용자가
다른 식별자를 언급해도 그 값이 Tool 조회에 쓰이지 않는다 (컴포넌트 설계서 4.4 위험 시나리오 대응).

주의: `tutor_chat_app.stream(...)`은 동기(sync) 제너레이터라, 그걸 순회하는 동안(=LLM
게이트웨이 응답을 기다리는 동안) 이 이벤트 루프가 막힌다. 이 프로젝트의 다른 라우트(HTTP
`/api/grading`, `/api/feedback`)도 전부 동기 SQLAlchemy/openai 클라이언트를 그대로 쓰는
동일한 방식이라 새로 생긴 문제는 아니지만, 여러 WS 연결을 동시에 받는 배포에서는 스레드
분리(`run_in_threadpool`) 등을 고려해야 한다 — 지금 단계(단일 사용자 확인용 프로토타입)에서는
범위 밖으로 남겨둔다.
"""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.agents.tutor_chat_graph import tutor_chat_app
from app.core.db import SessionLocal
from app.models import AnalysisSession, ChatMessage, ChatSession, User, UserAnswer
from app.services.chat_tools import ChatToolError, format_context_for_prompt, load_feedback_context

router = APIRouter(tags=["chat"])


def _get_or_create_chat_session(db: Session, result_id: str) -> ChatSession:
    chat_session = db.query(ChatSession).filter(ChatSession.result_id == result_id).one_or_none()
    if chat_session is None:
        chat_session = ChatSession(result_id=result_id)
        db.add(chat_session)
        db.commit()
        db.refresh(chat_session)
    return chat_session


@router.websocket("/api/chat")
async def chat_ws(websocket: WebSocket, result_id: str, user_identifier: str) -> None:
    await websocket.accept()
    db = SessionLocal()
    try:
        try:
            ctx = load_feedback_context(db, result_id)
        except ChatToolError as exc:
            await websocket.send_json({"type": "error", "detail": str(exc)})
            await websocket.close(code=4404)
            return

        # 세션 소유권 검사 (인증이 아닌 데이터 정합성 목적 — 컴포넌트 설계서 7절)
        user = db.query(User).filter(User.user_name == user_identifier).one_or_none()
        session = db.query(AnalysisSession).filter(AnalysisSession.session_id == ctx.session_id).one()
        if user is None or session.user_id != user.user_id:
            await websocket.send_json({"type": "error", "detail": "세션 소유자와 user_identifier가 일치하지 않습니다."})
            await websocket.close(code=4403)
            return

        chat_session = _get_or_create_chat_session(db, result_id)
        history_rows = (
            db.query(ChatMessage)
            .filter(ChatMessage.chat_id == chat_session.chat_id)
            .order_by(ChatMessage.created_at)
            .all()
        )
        history: list[dict[str, str]] = [{"role": m.role, "content": m.content} for m in history_rows]
        context_text = format_context_for_prompt(ctx)

        await websocket.send_json({"type": "ready", "history": history})

        while True:
            user_text = await websocket.receive_text()
            if not user_text.strip():
                continue

            db.add(ChatMessage(chat_id=chat_session.chat_id, role="user", content=user_text))
            db.commit()
            history.append({"role": "user", "content": user_text})

            graph_input = {"context_text": context_text, "history": history, "user_message": user_text}
            final_state: dict = {}
            try:
                # "custom" 모드 = chat_responder 노드가 writer()로 흘려보내는 텍스트 조각.
                # "values" 모드 = 각 노드 실행 후의 전체 state 스냅샷 — 마지막 값이 최종 결과.
                for stream_mode, payload in tutor_chat_app.stream(graph_input, stream_mode=["custom", "values"]):
                    if stream_mode == "custom":
                        await websocket.send_json({"type": "chunk", "content": payload})
                    elif stream_mode == "values":
                        final_state = payload
            except Exception as exc:  # 그래프 실행 자체가 예외를 던진 경우(설계상 흔치 않음)
                await websocket.send_json({"type": "error", "detail": f"응답 생성 실패: {exc}"})
                continue

            if final_state.get("blocked"):
                # 가드레일 차단 — chat_responder가 아예 실행되지 않아 chunk도, LLM 호출도 없었다.
                await websocket.send_json({"type": "blocked", "reason": final_state.get("block_reason", "")})
                continue

            if final_state.get("error"):
                await websocket.send_json({"type": "error", "detail": f"응답 생성 실패: {final_state['error']}"})
                continue

            reply = final_state.get("reply", "")
            db.add(ChatMessage(chat_id=chat_session.chat_id, role="assistant", content=reply))
            db.commit()
            history.append({"role": "assistant", "content": reply})

            await websocket.send_json({"type": "done"})
    except WebSocketDisconnect:
        pass
    finally:
        db.close()
