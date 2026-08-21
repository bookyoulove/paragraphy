import base64
import binascii
from typing import Annotated
from uuid import UUID

from agent.facade import stream_tutor_chat
from agent.schemas.tutor import TutorChatState
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from pydantic import BaseModel, Field
from shared.schema.tutor import TutorChatInput, TutorChatOutput
from sqlmodel import select

from backend.depends import (
    AnalysisResultDBDep,
    ChatMessageDBDep,
    ChatSessionDBDep,
    TutorChatAgentDep,
    UserDBDep,
    UserUUIDDep,
)
from backend.orm.models import AnalysisResults, AnalysisSessions, UserAnswers
from backend.schema.analysis_result.response import (
    AnalysisResultPublicWithProblemAnswer,
)
from backend.schema.chat_message.input import ChatMessageCreate
from backend.schema.chat_message.public import ChatMessagePublic
from backend.schema.chat_session.input import ChatSessionCreate
from backend.schema.problem.response import ProblemPublicWithRubrics
from backend.schema.user_answer.public import UserAnswerPublic

router = APIRouter(
    prefix="/results",
    tags=["results"],
)


class UserMessage(BaseModel):
    content: str


class ResultRanking(BaseModel):
    """A single answer's live rank among submitted answers to the same problem."""

    problem_id: UUID
    rank: int = Field(ge=1)
    attempt_count: int = Field(ge=1)
    percentile: float = Field(ge=0, le=100)
    score: float = Field(ge=1, le=5)
    score_scale: int = 5


def get_valid_result(
    result_id: UUID, user_id: UserUUIDDep, result_db: AnalysisResultDBDep
) -> AnalysisResults:
    result = result_db.get(result_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Result not found"
        )
    if result.user_answer.analysis_session.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to chat with this result",
        )
    return result


ValidResultDep = Annotated[AnalysisResults, Depends(get_valid_result)]


def _average_score(result: AnalysisResults) -> float:
    if not result.criteria_scores:
        raise ValueError("채점 항목 점수가 없습니다.")
    return sum(item.score for item in result.criteria_scores) / len(
        result.criteria_scores
    )


@router.get("/{result_id}/ranking", response_model=ResultRanking)
def get_result_ranking(
    result: ValidResultDep,
    result_db: AnalysisResultDBDep,
) -> ResultRanking:
    """Calculate a live rank without persisting a stale aggregate."""
    problem_id = result.user_answer.analysis_session.problem_id
    statement = (
        select(AnalysisResults)
        .join(UserAnswers, AnalysisResults.answer_id == UserAnswers.id)
        .join(AnalysisSessions, UserAnswers.session_id == AnalysisSessions.id)
        .where(AnalysisSessions.problem_id == problem_id)
    )
    attempts = [
        candidate
        for candidate in result_db.session.exec(statement).all()
        if candidate.criteria_scores
    ]
    if not attempts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="비교할 채점 결과가 없습니다.",
        )

    current_score = _average_score(result)
    higher_score_count = sum(
        _average_score(candidate) > current_score for candidate in attempts
    )
    attempt_count = len(attempts)
    rank = higher_score_count + 1  # 동점자는 같은 등수(competition ranking)다.
    percentile = (
        100.0
        if attempt_count == 1
        else round((attempt_count - rank) / (attempt_count - 1) * 100, 1)
    )
    return ResultRanking(
        problem_id=problem_id,
        rank=rank,
        attempt_count=attempt_count,
        percentile=percentile,
        score=round(current_score, 2),
    )


@router.post("/{result_id}/chat")
async def chat_with_tutor(
    result_id: UUID,
    message: UserMessage,
    result: ValidResultDep,
    chat_session_db: ChatSessionDBDep,
    chat_message_db: ChatMessageDBDep,
    chat_agent: TutorChatAgentDep,
) -> TutorChatOutput:
    if not result.chat_session:
        chat_session = chat_session_db.create(ChatSessionCreate(result_id=result_id))
    else:
        chat_session = result.chat_session

    chat_message_db.create(
        ChatMessageCreate(chat_id=chat_session.id, role="user", content=message.content)
    )

    history = chat_session.chat_messages
    problem = result.user_answer.analysis_session.problem
    user_answer = result.user_answer
    context = AnalysisResultPublicWithProblemAnswer(
        grammar_result=result.grammar_result,
        criteria_scores=result.criteria_scores,
        overall_comment=result.overall_comment,
        problem=ProblemPublicWithRubrics.model_validate(problem),
        user_answer=UserAnswerPublic.model_validate(user_answer),
    )

    ctx = context.model_dump_json()
    res = await chat_agent.run(
        TutorChatInput(
            context_text=ctx,
            history=history,
            user_identifier=str(result.user_answer.analysis_session.user_id),
            session_id=str(result.user_answer.analysis_session.id),
        )
    )

    chat_message_db.create(
        ChatMessageCreate(chat_id=chat_session.id, role="assistant", content=res.reply)
    )
    return res


@router.get("/{result_id}/chat", response_model=list[ChatMessagePublic])
async def retrive_chat(
    result_id: UUID,
    result: ValidResultDep,
):
    if not result.chat_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No chat session found"
        )

    history = result.chat_session.chat_messages
    return history


# WS /results/{result_id}/chat/ws — 스트리밍 + 가드레일이 적용된 Tutor Chat.
#
# 브라우저는 WebSocket 핸드셰이크에 커스텀 헤더(Authorization)를 실을 수 없으므로,
# HTTP 라우트가 쓰는 `AuthDep`(OAuth2PasswordBearer, Request 기반)을 그대로 재사용할 수
# 없다. 대신 로그인 시 발급한 토큰(사용자명을 base64 인코딩한 값)을 쿼리 파라미터로
# 받아 depends.get_current_user_id와 동일한 로직(디코드 -> 사용자 조회)을 여기서
# 그대로 수행한다.
#
# 메시지 프로토콜 (JSON):
#   서버 -> 클라이언트: {"type": "ready", "history": [...]}                (연결 직후, 과거 대화 이력)
#   클라이언트 -> 서버:  평문 텍스트 (질문 메시지)
#   서버 -> 클라이언트: {"type": "chunk", "content": "..."}                (스트리밍 조각, 여러 번)
#   서버 -> 클라이언트: {"type": "done"}                                   (스트리밍 끝, 정상 완료)
#   서버 -> 클라이언트: {"type": "blocked", "reason": "..."}               (입력 가드레일 차단)
#   서버 -> 클라이언트: {"type": "error", "detail": "..."}                 (오류 시, 연결은 유지)
@router.websocket("/{result_id}/chat/ws")
async def chat_with_tutor_ws(
    websocket: WebSocket,
    result_id: UUID,
    user_db: UserDBDep,
    result_db: AnalysisResultDBDep,
    chat_session_db: ChatSessionDBDep,
    chat_message_db: ChatMessageDBDep,
    token: str = Query(...),
) -> None:
    await websocket.accept()

    try:
        user_name = base64.b64decode(token).decode("utf-8")
    except binascii.Error, UnicodeDecodeError:
        user = None
    else:
        user = user_db.get_name(user_name)
    if user is None:
        await websocket.send_json(
            {"type": "error", "detail": "인증 토큰이 올바르지 않습니다."}
        )
        await websocket.close(code=4401)
        return

    result = result_db.get(result_id)
    if result is None:
        await websocket.send_json(
            {"type": "error", "detail": "채점 결과를 찾을 수 없습니다."}
        )
        await websocket.close(code=4404)
        return
    if result.user_answer.analysis_session.user_id != user.id:
        await websocket.send_json(
            {"type": "error", "detail": "이 채점 결과에 접근할 권한이 없습니다."}
        )
        await websocket.close(code=4403)
        return

    if not result.chat_session:
        chat_session = chat_session_db.create(ChatSessionCreate(result_id=result_id))
    else:
        chat_session = result.chat_session

    problem = result.user_answer.analysis_session.problem
    user_answer = result.user_answer
    context = AnalysisResultPublicWithProblemAnswer(
        grammar_result=result.grammar_result,
        criteria_scores=result.criteria_scores,
        overall_comment=result.overall_comment,
        problem=ProblemPublicWithRubrics.model_validate(problem),
        user_answer=UserAnswerPublic.model_validate(user_answer),
    )
    context_text = context.model_dump_json()
    user_identifier = str(result.user_answer.analysis_session.user_id)
    session_id = str(result.user_answer.analysis_session.id)

    # 대화가 진행되는 동안은 매 턴 DB를 다시 조회하지 않고, 이 메모리 상의 history에
    # 이어붙여 그래프 입력으로 재사용한다(WS 연결 시점에 검증한 result_id 기준 컨텍스트를
    # 그대로 유지 — 대화 중 다른 식별자가 언급되어도 영향받지 않는다).
    history: list[dict[str, str]] = [
        {"role": message.role, "content": message.content}
        for message in chat_session.chat_messages
    ]

    await websocket.send_json({"type": "ready", "history": history})

    try:
        while True:
            user_text = await websocket.receive_text()
            if not user_text.strip():
                continue

            chat_message_db.create(
                ChatMessageCreate(
                    chat_id=chat_session.id, role="user", content=user_text
                )
            )
            history.append({"role": "user", "content": user_text})

            chat_input = TutorChatInput(
                context_text=context_text,
                history=history,
                user_identifier=user_identifier,
                session_id=session_id,
            )
            final_state: TutorChatState | None = None
            try:
                # facade.stream_tutor_chat()이 그래프 실행을 Langfuse
                # "tutor-chat-request" span으로 감싸므로(guardrail_input/chat_responder
                # 노드 span이 이 span의 자식으로 기록됨), WS 라우트는 그래프 내부를
                # 몰라도 된다. "chunk" = 텍스트 조각, "state" = 최종 state 스냅샷.
                async for kind, payload in stream_tutor_chat(chat_input):
                    if kind == "chunk":
                        await websocket.send_json({"type": "chunk", "content": payload})
                    elif kind == "state":
                        final_state = payload
            except Exception as exc:  # noqa: BLE001
                await websocket.send_json(
                    {"type": "error", "detail": f"응답 생성 실패: {exc}"}
                )
                continue

            if final_state is None:
                await websocket.send_json(
                    {"type": "error", "detail": "응답 생성 실패: 알 수 없는 오류"}
                )
                continue

            if final_state.blocked:
                # 가드레일 차단 — chat_responder가 아예 실행되지 않아 chunk도, LLM 호출도 없었다.
                await websocket.send_json(
                    {"type": "blocked", "reason": final_state.block_reason}
                )
                continue

            if final_state.error:
                await websocket.send_json(
                    {"type": "error", "detail": f"응답 생성 실패: {final_state.error}"}
                )
                continue

            reply = final_state.reply
            chat_message_db.create(
                ChatMessageCreate(
                    chat_id=chat_session.id, role="assistant", content=reply
                )
            )
            history.append({"role": "assistant", "content": reply})

            await websocket.send_json({"type": "done"})
    except WebSocketDisconnect:
        pass
