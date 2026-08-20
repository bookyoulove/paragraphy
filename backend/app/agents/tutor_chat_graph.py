"""LangGraph 기반 Tutor Chat 에이전트.

그래프 구조:

    START -> guardrail_input -> (위험하면) END
                              -> chat_responder -> END

- guardrail_input: 사용자의 최신 채팅 메시지(`user_message`)를 LLM 호출 전에 먼저
  검사한다(grading_graph/feedback_graph와 동일한 `guardrail_service.check_input_safety`).
  위험하다고 판단되면 `blocked=True`를 세팅하고 즉시 END로 라우팅 — chat_responder는
  아예 실행되지 않으므로 스트리밍도, LLM 호출도 일어나지 않는다. 가드레일 호출 자체가
  실패하면(LLM 장애 등) 통과시킨다(fail-open, grading/feedback과 동일 원칙).
- chat_responder: `llm_client.chat_completion_stream()`으로 응답을 조각 단위로 받아
  LangGraph의 커스텀 스트림 채널(`get_stream_writer`)에 그때그때 흘려보낸다. 호출부
  (app/api/chat.py)는 `tutor_chat_app.stream(..., stream_mode=["custom", "values"])`로
  이 조각들을 실시간으로 받고, 동시에 최종 state(reply 전체)도 받는다.

컨텍스트(채점 결과·문제·모범답안·첨삭 결과) 로딩은 `chat_tools.py`(ToolExecutor)가
WS 연결/메시지 수신 시점에 API 레이어에서 미리 수행해 `context_text`로 넘겨준다
(다른 그래프들과 동일하게, 그래프 노드는 DB 세션을 직접 들고 있지 않는다).

질문 의도 분류(특정 오류/전체 피드백/수정 방법)는 별도 라우팅 노드로 분리하지 않고,
system 프롬프트 지시사항으로 처리한다 — 매 메시지마다 라우팅을 위한 추가 LLM 왕복을
만들면 채팅 응답 지연이 늘어나기 때문에, 응답 생성 1회 호출 안에서 판단하게 했다.
"""

from __future__ import annotations

from typing import Any, TypedDict

from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph

from app.services import guardrail_service
from app.services.llm_client import LLMClientError, chat_completion_stream

SYSTEM_PROMPT_TEMPLATE = """너는 대입 논술 답안 채점/첨삭 결과에 대한 학생의 후속 질문에 답하는
Tutor Chat 에이전트다. 아래는 이 학생의 최근 채점·첨삭 결과다.

{context_text}

지시사항:
- 학생 질문의 의도를 먼저 파악하라: (1) 특정 채점 항목의 점수 이유를 묻는지,
  (2) 전체적인 피드백 요약을 원하는지, (3) 구체적으로 어떻게 고치면 되는지 방법을
  묻는지. 의도에 맞춰 답의 초점을 맞춰라.
- 위에 제시된 채점 근거·개선 방향·첨삭 결과에 실제로 있는 내용만 근거로 답하라.
  없는 내용을 지어내지 마라.
- 학생에게 직접 말하듯 자연스러운 한국어 존댓말로, 간결하게 답하라. 장황한 서론 없이
  바로 답하라.
- 필요하면 학생 답안의 문장을 인용해도 좋다.
"""


class TutorChatState(TypedDict, total=False):
    # 입력
    context_text: str
    history: list[dict[str, str]]  # [{"role": "user"|"assistant", "content": str}, ...] (최신 사용자 메시지 포함)
    user_message: str  # 가드레일 검사 대상 = 이번에 새로 들어온 사용자 메시지
    # 가드레일
    blocked: bool
    block_reason: str
    # 출력
    reply: str
    error: str | None


def guardrail_input_node(state: TutorChatState) -> dict[str, Any]:
    result = guardrail_service.check_input_safety(state["user_message"])
    if result.flagged:
        return {"blocked": True, "block_reason": f"{result.category}: {result.reason}"}
    return {"blocked": False}


def _route_after_guardrail(state: TutorChatState) -> str:
    return END if state.get("blocked") else "chat_responder"


def chat_responder_node(state: TutorChatState) -> dict[str, Any]:
    writer = get_stream_writer()
    system_msg = {"role": "system", "content": SYSTEM_PROMPT_TEMPLATE.format(context_text=state["context_text"])}
    messages = [system_msg, *state["history"]]
    parts: list[str] = []
    try:
        for chunk in chat_completion_stream(messages, max_tokens=1024):
            parts.append(chunk)
            writer(chunk)  # app/api/chat.py가 stream_mode="custom"으로 실시간 수신
        return {"reply": "".join(parts), "error": None}
    except LLMClientError as exc:
        return {"reply": "".join(parts), "error": str(exc)}


def build_tutor_chat_graph():
    graph = StateGraph(TutorChatState)
    graph.add_node("guardrail_input", guardrail_input_node)
    graph.add_node("chat_responder", chat_responder_node)

    graph.add_edge(START, "guardrail_input")
    graph.add_conditional_edges(
        "guardrail_input", _route_after_guardrail, {"chat_responder": "chat_responder", END: END}
    )
    graph.add_edge("chat_responder", END)

    return graph.compile()


tutor_chat_app = build_tutor_chat_graph()