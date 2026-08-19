"""문제에 맞는 초안 루브릭을 생성하는 그래프."""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph

from agent.integrations import retrieval
from agent.model import get_structured_model
from agent.schemas.rubric import RubricGenerationOutput, RubricState

MAX_ATTEMPTS = 3
RAG_TOP_K = 6

logger = logging.getLogger(__name__)


def rag_agent_node(state: RubricState) -> dict[str, str]:
    try:
        results = retrieval.query(
            state.request.content, n_results=RAG_TOP_K, where={"source": "국립국어원"}
        )
    except Exception:
        logger.exception("Rubric RAG retrieval failed")
        results: list[retrieval.RetrievedChunk] = []
    context = "\n\n---\n\n".join(
        f"[{item['metadata'].get('doc_type', '')}"
        f"{'/' + item['metadata']['rubric_item'] if item['metadata'].get('rubric_item') else ''}] {item['text']}"
        for item in results
    )
    return {"rag_context": context}


def _build_prompt(state: RubricState) -> str:
    model_answer = state.request.model_answer or "(제공되지 않음)"
    rag_context = state.rag_context or "(참고자료 없음)"
    return f"""너는 대입 논술 문제의 채점 기준을 설계하는 Rubric Agent다. 문제의 성격과 모범답안을
참고해 사용자가 수정할 수 있는 초안 루브릭을 제안하라. 각 항목의 max_score는 5로 고정한다.
description에는 1~5점 수준을 판단하는 핵심 기준을 한두 문장으로 작성하라.

문제:
{state.request.content}

모범답안:
{model_answer}

참고 자료:
{rag_context}

국립국어원 9개 준거를 그대로 복사하지 말고, 이 문제의 제시문 유무·요약/논증 유형·분량 등에
맞게 5~9개를 제안하라. 참고 자료는 초안 설계에만 활용하라."""


def rubric_agent_node(state: RubricState) -> dict[str, Any]:
    base_prompt = _build_prompt(state)
    last_error = ""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        prompt = base_prompt
        if attempt > 1:
            prompt += (
                f"\n\n이전 구조화 출력이 실패했다. 오류: {last_error}. 다시 시도하라."
            )
        try:
            result = get_structured_model(RubricGenerationOutput).invoke(
                [HumanMessage(content=prompt)]
            )
            rubrics = [
                item.model_copy(update={"max_score": 5}) for item in result.rubrics
            ]
            return {"rubrics": rubrics, "error": None}
        except Exception as exc:
            logger.exception("Rubric model attempt %d failed", attempt)
            last_error = str(exc)

    return {
        "rubrics": [],
        "error": f"Rubric Agent가 {MAX_ATTEMPTS}회 시도 후에도 실패했습니다: {last_error}",
    }


def build_rubric_graph():
    graph = StateGraph(RubricState)
    graph.add_node("rag_agent", rag_agent_node)
    graph.add_node("rubric_agent", rubric_agent_node)
    graph.add_edge(START, "rag_agent")
    graph.add_edge("rag_agent", "rubric_agent")
    graph.add_edge("rubric_agent", END)
    return graph.compile()


rubric_app = build_rubric_graph()
