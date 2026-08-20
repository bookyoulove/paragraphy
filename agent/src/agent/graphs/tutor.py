"""채점/첨삭 결과에 대한 Tutor Chat 그래프."""

from __future__ import annotations

import logging

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langfuse import observe
from langgraph.graph import END, START, StateGraph

from agent.integrations.prompts import get_prompt
from agent.model import get_chat_model
from agent.retry import call_with_retry
from agent.schemas.tutor import TutorChatState

logger = logging.getLogger(__name__)


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
    try:
        model = get_chat_model()
        response = call_with_retry(
            lambda: model.invoke(messages),
            operation_name="Tutor model",
            max_attempts=2,
            max_wait=5,
        )
        return {"reply": str(response.content), "error": None}
    except Exception as exc:
        logger.exception("Tutor model invocation failed")
        return {"reply": "", "error": str(exc)}


def build_tutor_chat_graph():
    graph = StateGraph(TutorChatState)
    graph.add_node("chat_responder", chat_responder_node)
    graph.add_edge(START, "chat_responder")
    graph.add_edge("chat_responder", END)
    return graph.compile()


tutor_chat_app = build_tutor_chat_graph()
