"""Supervisor, 가드레일, RAG, 채점으로 구성된 논술 채점 그래프."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from langchain_core.messages import HumanMessage
from langfuse import observe
from langgraph.graph import END, START, StateGraph
from shared.schema.rubric import Rubric

from agent.config import settings
from agent.integrations import retrieval
from agent.integrations.prompts import get_prompt
from agent.integrations.spelling import (
    SpellingIntegrationError,
    check_spelling,
)
from agent.model import get_structured_model
from agent.nodes import guardrails
from agent.retry import StructuredOutputError, ainvoke_with_retry
from agent.schemas.grading import (
    CriterionScore,
    GradingOutput,
    GradingState,
    GrammarError,
    RubricItem,
)

MAX_ATTEMPTS = 3
RAG_TOP_K = 4

logger = logging.getLogger(__name__)


def _rubric_item_suffix(metadata: dict[str, object]) -> str:
    rubric_item = metadata.get("rubric_item")
    return f"/{rubric_item}" if isinstance(rubric_item, str) and rubric_item else ""


def _format_rubric(items: list[RubricItem]) -> str:
    return "\n".join(
        f"{idx}. {item.criteria} (0~5점) — {item.description or '(설명 없음)'}"
        for idx, item in enumerate(items, 1)
    )


def _build_prompt(state: GradingState) -> str:
    problem = state.request.problem
    rubric_text = _format_rubric(state.rubric_items)
    model_answer = problem.model_answer or "(제공되지 않음)"
    rag_block = f"\n\n참고 자료:\n{state.rag_context}" if state.rag_context else ""
    return get_prompt(
        "grading-agent",
        problem_content=problem.content,
        model_answer=model_answer,
        rubric_text=rubric_text,
        rag_block=rag_block,
        user_answer=state.request.user_answer,
    )


type RawRubric = Rubric | RubricItem | Mapping[str, str | None]


def _normalise_rubrics(
    raw_items: Sequence[RawRubric],
) -> list[RubricItem]:
    normalised: list[RubricItem] = []
    for item in raw_items:
        if isinstance(item, RubricItem):
            normalised.append(item)
            continue
        if isinstance(item, Mapping):
            criteria_value = item.get("criteria")
            description_value = item.get("description")
            criteria = criteria_value if isinstance(criteria_value, str) else ""
            description = (
                description_value if isinstance(description_value, str) else ""
            )
        else:
            criteria = item.criteria
            description = item.description or ""
        normalised.append(
            RubricItem(criteria=criteria, description=description, max_score=5)
        )
    return normalised


def _normalise_result(
    result: GradingOutput, rubric_items: list[RubricItem]
) -> tuple[list[CriterionScore], float, str]:
    if not result.criteria_scores:
        raise ValueError("criteria_scores가 비어 있습니다.")

    scores = result.criteria_scores
    if len(scores) != len(rubric_items):
        raise ValueError(
            "채점 결과 항목 수가 채점 기준 수와 일치하지 않습니다. "
            f"(기준 {len(rubric_items)}개, 결과 {len(scores)}개)"
        )
    scores = [
        score.model_copy(update={"criterion": rubric.criteria})
        for score, rubric in zip(scores, rubric_items)
    ]
    total_score = float(sum(score.score for score in scores))
    return scores, total_score, result.overall_comment


@observe(name="grading:supervisor", as_type="span")
def supervisor_node(state: GradingState) -> dict[str, object]:
    rubric_items = _normalise_rubrics(state.request.problem.rubrics)
    if not rubric_items:
        return {"error": "채점 기준(rubric_items)이 비어 있습니다."}
    if not state.request.user_answer.strip():
        return {"error": "학생 답안(user_answer)이 비어 있습니다."}
    return {"rubric_items": rubric_items}


def _route_after_supervisor(state: GradingState) -> str:
    return END if state.error else "guardrail_input"


@observe(name="grading:guardrail_input", as_type="span")
def guardrail_input_node(state: GradingState) -> dict[str, object]:
    result = guardrails.check_input_safety(state.request.user_answer)
    if result.flagged:
        return {"error": f"입력 검증에서 차단됨 ({result.category}): {result.reason}"}
    return {}


def _route_after_guardrail_input(state: GradingState) -> str:
    return END if state.error else "rag_agent"


@observe(name="grading:rag_agent", as_type="span")
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
        logger.exception("Grading RAG retrieval failed")
        results: list[retrieval.RetrievedChunk] = []

    context = "\n\n---\n\n".join(
        f"[{item['metadata'].get('source', '')}/{item['metadata'].get('doc_type', '')}"
        f"{_rubric_item_suffix(item['metadata'])}] {item['text']}"
        for item in results
    )
    return {"rag_context": context}


@observe(name="grading:grammar_agent", as_type="span")
def grammar_agent_node(state: GradingState) -> dict[str, object]:
    essay_text = state.request.user_answer
    try:
        result = check_spelling(essay_text)
        return {
            "grammar_result": result,
            "grammar_error": None,
        }
    except SpellingIntegrationError as exc:
        logger.exception("Grammar integration failed")
        return {
            "revised_text": essay_text,
            "grammar_error": str(exc),
        }


@dataclass(frozen=True)
class _GradingRun:
    scores: list[CriterionScore]
    total_score: float
    overall_comment: str
    grammar_errors: list[GrammarError]


def _aggregate_grading_runs(runs: Sequence[_GradingRun]) -> _GradingRun:
    """여러 채점 결과를 항목별 중위값과 대표 설명으로 합친다."""
    if not runs:
        raise ValueError("채점 결과가 없습니다.")

    median_scores = [
        sorted(run.scores[index].score for run in runs)[len(runs) // 2]
        for index in range(len(runs[0].scores))
    ]
    distances = [
        sum(
            abs(score.score - median_score)
            for score, median_score in zip(run.scores, median_scores)
        )
        for run in runs
    ]
    representative = runs[distances.index(min(distances))]
    scores = [
        score.model_copy(update={"score": median_score})
        for score, median_score in zip(representative.scores, median_scores)
    ]
    return _GradingRun(
        scores=scores,
        total_score=float(sum(median_scores)),
        overall_comment=representative.overall_comment,
        grammar_errors=representative.grammar_errors,
    )


@observe(name="grading:grading_agent", as_type="span")
async def grading_agent_node(state: GradingState) -> dict[str, object]:
    base_prompt = _build_prompt(state)

    try:
        model = get_structured_model(
            GradingOutput,
            temperature=settings.ai_cloud_grading_temperature,
        )

        async def invoke(
            prompt: str,
        ) -> _GradingRun:
            result = await model.ainvoke([HumanMessage(content=prompt)])
            try:
                scores, total_score, overall_comment = _normalise_result(
                    result, state.rubric_items
                )
            except (AttributeError, KeyError, TypeError, ValueError) as exc:
                raise StructuredOutputError(str(exc)) from exc
            return _GradingRun(
                scores=scores,
                total_score=total_score,
                overall_comment=overall_comment,
                grammar_errors=result.grammar_errors,
            )

        async def run_replica(replica_number: int) -> _GradingRun:
            return await ainvoke_with_retry(
                invoke,
                base_prompt,
                operation_name=f"Grading model replica {replica_number}",
                max_attempts=MAX_ATTEMPTS,
            )

        # ainvoke + gather로 세 요청을 동시에 전송한다. 따라서 네트워크가 허용하는
        # 범위에서는 세 번의 최대 지연시간만 기다리고, 순차 호출처럼 3배를 기다리지 않는다.
        runs = await asyncio.gather(
            *(
                run_replica(number)
                for number in range(1, settings.ai_cloud_grading_replicas + 1)
            )
        )
        aggregated = _aggregate_grading_runs(runs)
        return {
            "criteria_scores": aggregated.scores,
            "total_score": aggregated.total_score,
            "overall_comment": aggregated.overall_comment,
            "grammar_errors": aggregated.grammar_errors,
            "error": None,
        }
    except Exception as exc:
        logger.exception("Grading model invocation failed")
        return {
            "error": (
                f"채점 에이전트가 {settings.ai_cloud_grading_replicas}회 병렬 생성 후에도 실패했습니다: {exc}"
            )
        }


@observe(name="grading:guardrail_output", as_type="span")
def guardrail_output_node(state: GradingState) -> dict[str, object]:
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
