"""채점/첨삭 결과에 대한 Tutor Chat 그래프."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from agent.model import get_chat_model
from agent.schemas.tutor import TutorChatState

SYSTEM_PROMPT_TEMPLATE = """너는 대입 논술 답안 채점/첨삭 결과에 대한 학생의 후속 질문에 답하는 Tutor Chat
에이전트다. 아래는 이 학생의 최근 채점·첨삭 결과다.

{context_text}

학생 질문의 의도를 파악해 점수 이유, 전체 피드백 요약, 구체적인 수정 방법 중 필요한 부분에
집중해 답하라. 위 결과에 실제로 있는 내용만 근거로 삼고 없는 내용을 지어내지 마라. 학생에게
직접 말하듯 자연스러운 한국어 존댓말로 간결하게 답하라."""


def chat_responder_node(state: TutorChatState) -> dict[str, Any]:
    messages = [
        SystemMessage(
            content=SYSTEM_PROMPT_TEMPLATE.format(context_text=state["context_text"])
        ),
        *[
            HumanMessage(content=message.content)
            if message.role == "user"
            else AIMessage(content=message.content)
            for message in state["history"]
        ],
    ]
    try:
        response = get_chat_model().invoke(messages)
        return {"reply": str(response.content), "error": None}
    except Exception as exc:
        return {"reply": "", "error": str(exc)}


def build_tutor_chat_graph():
    graph = StateGraph(TutorChatState)  # type: ignore[arg-type]
    graph.add_node("chat_responder", chat_responder_node)
    graph.add_edge(START, "chat_responder")
    graph.add_edge("chat_responder", END)
    return graph.compile()


tutor_chat_app = build_tutor_chat_graph()
