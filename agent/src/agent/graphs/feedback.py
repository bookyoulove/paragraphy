"""문법/표현 첨삭 그래프."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph

from agent.integrations import retrieval
from agent.integrations.spelling import (
    SpellingIntegrationError,
    check_spelling,
    derive_corrections,
)
from agent.model import get_structured_model
from agent.nodes import guardrails
from agent.schemas.feedback import (
    FeedbackState,
    PolishOutput,
    SpellingCorrection,
)

MAX_ATTEMPTS = 3
RAG_QUERY = "문장과 어휘 표현이 자연스럽고 논증에 효과적인가, 어문 규범과 글쓰기 관습을 지키는가"
RAG_TOP_K = 3


def guardrail_input_node(state: FeedbackState) -> dict[str, Any]:
    result = guardrails.check_input_safety(state["essay_text"])
    if result.flagged:
        return {"error": f"입력 검증에서 차단됨 ({result.category}): {result.reason}"}
    return {}


def _route_after_guardrail_input(state: FeedbackState) -> str:
    return END if state.get("error") else "spelling_agent"


def spelling_agent_node(state: FeedbackState) -> dict[str, Any]:
    essay_text = state["essay_text"]
    try:
        result = check_spelling(essay_text)
        return {
            "grammar_result": result,
            "revised_text": result.revised,
            "spelling_corrections": [
                SpellingCorrection(
                    original=item.original,
                    revised=item.revised,
                    category=item.category,
                    comment=item.comment,
                )
                for item in derive_corrections(result)
            ],
            "spelling_error": None,
        }
    except SpellingIntegrationError as exc:
        return {
            "revised_text": essay_text,
            "spelling_corrections": [],
            "spelling_error": str(exc),
        }


def _build_polish_prompt(state: FeedbackState, rag_context: str) -> str:
    corrections = state.get("spelling_corrections") or []
    corrections_text = (
        "\n".join(
            f"- '{item.original}' → '{item.revised}' ({item.category}: {item.comment})"
            for item in corrections
        )
        or "(맞춤법 교정 사항 없음)"
    )
    rag_block = f"\n\n참고 자료:\n{rag_context}" if rag_context else ""
    return f"""너는 논술 답안의 문장과 표현을 다듬는 첨삭 에이전트다. 맞춤법/띄어쓰기가 아니라
문장 구조, 어휘 선택, 논증 효과 관점에서 실제로 필요한 윤문 제안만 만들어라. 문제가 없으면
제안 목록을 비워라. 학생 답안을 완성해 주지 말고, 스스로 고칠 수 있는 방향을 제시하라.

원문:
{state["essay_text"]}

이미 처리된 맞춤법 교정(중복 지적 금지):
{corrections_text}
{rag_block}"""


def polish_agent_node(state: FeedbackState) -> dict[str, Any]:
    try:
        rag_results = retrieval.query(RAG_QUERY, n_results=RAG_TOP_K)
    except Exception:
        rag_results: list[retrieval.RetrievedChunk] = []
    rag_context = "\n\n---\n\n".join(
        f"[{item['metadata'].get('source', '')}/{item['metadata'].get('doc_type', '')}] {item['text']}"
        for item in rag_results
    )

    base_prompt = _build_polish_prompt(state, rag_context)
    last_error = ""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        prompt = base_prompt
        if attempt > 1:
            prompt += (
                f"\n\n이전 구조화 출력이 실패했다. 오류: {last_error}. 다시 시도하라."
            )
        try:
            result = get_structured_model(PolishOutput).invoke(
                [HumanMessage(content=prompt)]
            )
            return {
                "polish_suggestions": result.polish_suggestions,
                "overall_comment": result.overall_comment,
                "error": None,
            }
        except Exception as exc:
            last_error = str(exc)

    return {
        "polish_suggestions": [],
        "overall_comment": "",
        "error": f"윤문 제안 생성이 {MAX_ATTEMPTS}회 시도 후에도 실패했습니다: {last_error}",
    }


def build_feedback_graph():
    graph = StateGraph(FeedbackState)  # type: ignore[arg-type]
    graph.add_node("guardrail_input", guardrail_input_node)
    graph.add_node("spelling_agent", spelling_agent_node)
    graph.add_node("polish_agent", polish_agent_node)
    graph.add_edge(START, "guardrail_input")
    graph.add_conditional_edges(
        "guardrail_input",
        _route_after_guardrail_input,
        {"spelling_agent": "spelling_agent", END: END},
    )
    graph.add_edge("spelling_agent", "polish_agent")
    graph.add_edge("polish_agent", END)
    return graph.compile()


feedback_app = build_feedback_graph()
