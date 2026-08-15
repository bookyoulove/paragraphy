"""LangGraph 기반 Tutor Chat 에이전트.

그래프 구조:

    START -> chat_responder -> END

컨텍스트(채점 결과·문제·모범답안·첨삭 결과) 로딩은 `chat_tools.py`(ToolExecutor)가
WS 연결/메시지 수신 시점에 API 레이어에서 미리 수행해 `context_text`로 넘겨준다
(다른 그래프들과 동일하게, 그래프 노드는 DB 세션을 직접 들고 있지 않는다).

질문 의도 분류(특정 오류/전체 피드백/수정 방법)는 별도 라우팅 노드로 분리하지 않고,
system 프롬프트 지시사항으로 처리한다 — 매 메시지마다 라우팅을 위한 추가 LLM 왕복을
만들면 채팅 응답 지연이 늘어나기 때문에, 응답 생성 1회 호출 안에서 판단하게 했다.
"""

from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.services.llm_client import LLMClientError, chat_completion

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
    context_text: str
    history: list[dict[str, str]]  # [{"role": "user"|"assistant", "content": str}, ...]
    reply: str
    error: str | None


def chat_responder_node(state: TutorChatState) -> dict[str, Any]:
    system_msg = {"role": "system", "content": SYSTEM_PROMPT_TEMPLATE.format(context_text=state["context_text"])}
    messages = [system_msg, *state["history"]]
    try:
        reply = chat_completion(messages, max_tokens=1024)
        return {"reply": reply, "error": None}
    except LLMClientError as exc:
        return {"reply": "", "error": str(exc)}


def build_tutor_chat_graph():
    graph = StateGraph(TutorChatState)
    graph.add_node("chat_responder", chat_responder_node)
    graph.add_edge(START, "chat_responder")
    graph.add_edge("chat_responder", END)
    return graph.compile()


tutor_chat_app = build_tutor_chat_graph()
