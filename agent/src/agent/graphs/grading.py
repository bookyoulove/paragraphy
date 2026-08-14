"""Supervisor, 가드레일, RAG, 채점으로 구성된 논술 채점 그래프."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph

from agent.integrations import retrieval
from agent.integrations.spelling import (
    SpellingIntegrationError,
    check_spelling,
)
from agent.model import get_structured_model
from agent.nodes import guardrails
from agent.schemas.grading import (
    CriterionScore,
    GradingOutput,
    GradingState,
    RubricItem,
)

MAX_ATTEMPTS = 3
RAG_TOP_K = 4


def _format_rubric(items: list[RubricItem]) -> str:
    return "\n".join(
        f"{idx}. {item.criteria} (5점 만점) — {item.description or '(설명 없음)'}"
        for idx, item in enumerate(items, 1)
    )


def _build_prompt(state: GradingState) -> str:
    problem = state.request.problem
    rubric_text = _format_rubric(state.rubric_items)
    model_answer = problem.model_answer or "(제공되지 않음)"
    rag_block = f"\n\n참고 자료:\n{state.rag_context}" if state.rag_context else ""
    return f"""너는 대입 논술 답안을 채점하는 채점 에이전트다. 채점 기준에 따라 학생 답안을
항목별 1~5점으로 평가하고, 각 점수의 구체적인 근거와 학생이 스스로 개선할 수 있는 방향을
제시하라. 개선 방향은 완성된 답안이나 문단을 대신 쓰지 말고 작성 방향만 안내하라.

문제:
{problem.content}

모범답안(참고용):
{model_answer}

채점 기준:
{rubric_text}
{rag_block}

학생 답안:
{state.request.user_answer}

채점 기준과 같은 순서와 개수로 결과를 작성하라. criterion은 기준의 이름을 그대로 사용하라.
참고 자료는 채점 판단의 근거로만 사용하고 학생 답안과 혼동하지 마라."""


def _normalise_rubrics(raw_items: list[Any]) -> list[RubricItem]:
    normalised: list[RubricItem] = []
    for item in raw_items:
        if isinstance(item, RubricItem):
            normalised.append(item)
            continue
        criteria = item.get("criteria", "") if isinstance(item, dict) else item.criteria
        description = (
            item.get("description", "") if isinstance(item, dict) else item.description
        ) or ""
        normalised.append(
            RubricItem(criteria=criteria, description=description, max_score=5)
        )
    return normalised


def _normalise_result(
    result: Any, rubric_items: list[RubricItem]
) -> tuple[list[CriterionScore], float, str]:
    if not result.criteria_scores:
        raise ValueError("criteria_scores가 비어 있습니다.")

    scores = result.criteria_scores
    if len(scores) == len(rubric_items):
        scores = [
            score.model_copy(update={"criterion": rubric.criteria})
            for score, rubric in zip(scores, rubric_items)
        ]
    total_score = float(sum(score.score for score in scores))
    return scores, total_score, result.overall_comment


def supervisor_node(state: GradingState) -> dict[str, Any]:
    rubric_items = _normalise_rubrics(state.request.problem.rubrics)
    if not rubric_items:
        return {"error": "채점 기준(rubric_items)이 비어 있습니다."}
    if not state.request.user_answer.strip():
        return {"error": "학생 답안(user_answer)이 비어 있습니다."}
    return {"rubric_items": rubric_items}


def _route_after_supervisor(state: GradingState) -> str:
    return END if state.error else "guardrail_input"


def guardrail_input_node(state: GradingState) -> dict[str, Any]:
    result = guardrails.check_input_safety(state.request.user_answer)
    if result.flagged:
        return {"error": f"입력 검증에서 차단됨 ({result.category}): {result.reason}"}
    return {}


def _route_after_guardrail_input(state: GradingState) -> str:
    return END if state.error else "rag_agent"


def rag_agent_node(state: GradingState) -> dict[str, str]:
    problem = state.request.problem
    query_text = (
        problem.content
        + "\n"
        + "\n".join(
            f"{item.criteria}: {item.description}" for item in state.rubric_items
        )
    )
    university = getattr(problem, "university", None)
    try:
        results = retrieval.query(
            query_text,
            n_results=RAG_TOP_K,
            where={"university": university} if university else None,
        )
        if not results and university:
            results = retrieval.query(query_text, n_results=RAG_TOP_K)
    except Exception:
        results: list[retrieval.RetrievedChunk] = []

    context = "\n\n---\n\n".join(
        f"[{item['metadata'].get('source', '')}/{item['metadata'].get('doc_type', '')}"
        f"{'/' + item['metadata']['rubric_item'] if item['metadata'].get('rubric_item') else ''}] {item['text']}"
        for item in results
    )
    return {"rag_context": context}


def grammar_agent_node(state: GradingState) -> dict[str, Any]:
    essay_text = state.request.user_answer
    try:
        result = check_spelling(essay_text)
        return {
            "grammar_result": result,
            "grammar_error": None,
        }
    except SpellingIntegrationError as exc:
        return {
            "revised_text": essay_text,
            "grammar_error": str(exc),
        }


def grading_agent_node(state: GradingState) -> dict[str, Any]:
    base_prompt = _build_prompt(state)
    last_error = ""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        prompt = base_prompt
        if attempt > 1:
            prompt += (
                f"\n\n이전 구조화 출력이 실패했다. 오류: {last_error}. 다시 시도하라."
            )
        try:
            result = get_structured_model(GradingOutput).invoke(
                [HumanMessage(content=prompt)]
            )
            scores, total_score, overall_comment = _normalise_result(
                result, state.rubric_items
            )
            return {
                "criteria_scores": scores,
                "total_score": total_score,
                "overall_comment": overall_comment,
                "grammar_errors": result.grammar_errors,
                "error": None,
            }
        except Exception as exc:
            last_error = str(exc)

    return {
        "error": f"채점 에이전트가 {MAX_ATTEMPTS}회 시도 후에도 실패했습니다: {last_error}"
    }


def guardrail_output_node(state: GradingState) -> dict[str, Any]:
    if state.error:
        return {}
    result = guardrails.check_direct_writing(state.criteria_scores)
    return {"policy_warning": result.reason if result.flagged else None}


def build_grading_graph():
    graph = StateGraph(GradingState)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("guardrail_input", guardrail_input_node)
    graph.add_node("rag_agent", rag_agent_node)
    graph.add_node("grammar_agent", grammar_agent_node)
    graph.add_node("grading_agent", grading_agent_node)
    graph.add_node("guardrail_output", guardrail_output_node)
    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        _route_after_supervisor,
        {"guardrail_input": "guardrail_input", END: END},
    )
    graph.add_conditional_edges(
        "guardrail_input",
        _route_after_guardrail_input,
        {"rag_agent": "rag_agent", END: END},
    )
    graph.add_edge("rag_agent", "grammar_agent")
    graph.add_edge("grammar_agent", "grading_agent")
    graph.add_edge("grading_agent", "guardrail_output")
    graph.add_edge("guardrail_output", END)
    return graph.compile()


grade_app = build_grading_graph()
grading_app = grade_app
