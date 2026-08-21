"""채점/첨삭 결과에 대한 Tutor Chat 그래프.

그래프 구조:

    START -> guardrail_input -> (위험하면) END
                              -> chat_responder -> END

- guardrail_input: 이번에 새로 들어온 사용자 메시지(history의 마지막 user 턴)를
  LLM 호출 전에 먼저 검사한다(grading_graph와 동일한 `guardrails.check_input_safety`).
  위험하다고 판단되면 `blocked=True`를 세팅하고 즉시 END로 라우팅 — chat_responder는
  아예 실행되지 않으므로 스트리밍도, LLM 호출도 일어나지 않는다. 가드레일 호출 자체가
  실패하면(LLM 장애 등) 통과시킨다(fail-open, grading/feedback과 동일 원칙).
- chat_responder: LangChain 채팅 모델의 `.stream()`으로 응답을 조각 단위로 받아
  LangGraph의 커스텀 스트림 채널(`get_stream_writer`)에 그때그때 흘려보낸다. 호출부
  (WS 라우트)는 `tutor_chat_app.stream(..., stream_mode=["custom", "values"])`로
  이 조각들을 실시간으로 받고, 동시에 최종 state(reply 전체)도 받는다.
  이미 일부 조각을 흘려보낸 뒤에 재시도하면 클라이언트 쪽 스트리밍 버블에 이전 시도의
  조각과 재시도 조각이 섞여 보이므로, 이 노드는 `call_with_retry`로 감싸지 않는다
  (구조화 출력이 아니라 텍스트 스트림이라 재시도 시 이어붙이기 안전성을 보장할 수 없음).
"""

from __future__ import annotations

import logging

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langfuse import observe
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph

from agent.integrations.prompts import get_prompt
from agent.model import get_chat_model
from agent.nodes import guardrails
from agent.schemas.tutor import TutorChatState

logger = logging.getLogger(__name__)


def _latest_user_message(state: TutorChatState) -> str:
    for message in reversed(state.request.history):
        if message.role == "user":
            return message.content
    return ""


@observe(name="tutor:guardrail_input", as_type="span")
def guardrail_input_node(state: TutorChatState) -> dict[str, object]:
    result = guardrails.check_input_safety(_latest_user_message(state))
    if result.flagged:
        return {
            "blocked": True,
            "block_reason": f"{result.category}: {result.reason}",
        }
    return {"blocked": False}


def _route_after_guardrail(state: TutorChatState) -> str:
    return END if state.blocked else "chat_responder"


@observe(name="tutor:chat_responder", as_type="span")
def chat_responder_node(state: TutorChatState) -> dict[str, object]:
    messages = [
        SystemMessage(
            content=get_prompt(
                "tutor-chat-agent", context_text=state.request.context_text
            )
        ),
        *[
            HumanMessage(content=message.content)
            if message.role == "user"
            else AIMessage(content=message.content)
            for message in state.request.history
        ],
    ]
    writer = get_stream_writer()
    parts: list[str] = []
    try:
        model = get_chat_model()
        for chunk in model.stream(messages):
            text = str(chunk.content)
            if not text:
                continue
            parts.append(text)
            writer(text)  # WS 라우트가 stream_mode="custom"으로 실시간 수신
        return {"reply": "".join(parts), "error": None}
    except Exception as exc:
        logger.exception("Tutor model invocation failed")
        return {"reply": "".join(parts), "error": str(exc)}


def build_tutor_chat_graph():
    graph = StateGraph(TutorChatState)
    graph.add_node("guardrail_input", guardrail_input_node)
    graph.add_node("chat_responder", chat_responder_node)
    graph.add_edge(START, "guardrail_input")
    graph.add_conditional_edges(
        "guardrail_input",
        _route_after_guardrail,
        {"chat_responder": "chat_responder", END: END},
    )
    graph.add_edge("chat_responder", END)
    return graph.compile()


tutor_chat_app = build_tutor_chat_graph()