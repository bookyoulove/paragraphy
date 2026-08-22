"""키워드 기반 문제 추천: 하이브리드(키워드+RAG) 검색, 없으면 LLM 생성."""

from __future__ import annotations

import asyncio
import logging

from langchain_core.messages import HumanMessage
from langfuse import observe
from langgraph.graph import END, START, StateGraph
from shared.schema.recommend import (
    GeneratedProblem,
    RecommendedProblem,
    RecommendRequest,
    RecommendResult,
)

from agent.integrations import retrieval
from agent.integrations.retrieval import RetrievedChunk
from agent.integrations.writing_prompts import SOURCE, ensure_indexed, load_items
from agent.model import get_structured_model
from agent.nodes import guardrails
from agent.retry import invoke_with_retry
from agent.schemas.recommend import GeneratedProblemOutput, RecommendState

logger = logging.getLogger(__name__)

TOP_K = 8
MAX_MATCHES = 5
DISTANCE_THRESHOLD = 1.0
MAX_ATTEMPTS = 3


def _to_problem(item: dict[str, object]) -> RecommendedProblem:
    return RecommendedProblem(
        label=str(item.get("label", "")),
        category=str(item.get("category", "")),
        title=str(item.get("title", "")),
        content=str(item.get("content", "")),
    )


def _keyword_scan(keyword: str) -> list[RecommendedProblem]:
    """전체 코퍼스(38개)를 훑는 정확/부분 문자열 매칭 - 키워드 계층."""
    keyword_norm = keyword.strip()
    if not keyword_norm:
        return []
    try:
        items = load_items()
    except Exception:
        logger.exception("Failed to load writing prompts corpus for keyword scan")
        return []
    return [
        _to_problem(item)
        for item in items
        if keyword_norm in item.get("title", "")
        or keyword_norm in item.get("content", "")
    ]


def _semantic_search(
    keyword: str, exclude_labels: set[str]
) -> list[RecommendedProblem]:
    """chroma 임베딩 기반 최근접 이웃 검색 - 시맨틱(유사어) 계층."""
    ensure_indexed()
    results: list[RetrievedChunk]
    try:
        results = retrieval.query(keyword, n_results=TOP_K, where={"source": SOURCE})
    except Exception:
        logger.exception("Writing-prompt retrieval failed")
        results = []

    scored: list[tuple[float, RecommendedProblem]] = []
    for item in results:
        meta = item["metadata"]
        label = str(meta.get("label", ""))
        if label in exclude_labels or item["distance"] > DISTANCE_THRESHOLD:
            continue
        scored.append(
            (
                item["distance"],
                RecommendedProblem(
                    label=label,
                    category=str(meta.get("category", "")),
                    title=str(meta.get("title", "")),
                    content=item["text"],
                ),
            )
        )

    def distance_key(pair: tuple[float, RecommendedProblem]) -> float:
        return pair[0]

    scored.sort(key=distance_key)
    return [problem for _, problem in scored]


def _hybrid_search(keyword: str) -> list[RecommendedProblem]:
    exact_matches = _keyword_scan(keyword)
    exclude_labels = {problem.label for problem in exact_matches}
    semantic_matches = _semantic_search(keyword, exclude_labels)
    return (exact_matches + semantic_matches)[:MAX_MATCHES]


def _build_generation_prompt(keyword: str) -> str:
    return f"""너는 대입 논술 학습 플랫폼의 문제 출제 담당자다. 다음 학습 목표를 반영해 새로운
논증적 글쓰기 문항을 하나 작성하라.

학습 목표: {keyword}

형식 요구사항:
- title: 문제의 핵심 쟁점을 나타내는 간결한 명사구 (예: "동물원 폐지", "로봇세 도입")
- content: 쟁점의 배경을 설명하는 한두 문단(200~400자)과 찬반이 갈리는 사회적 쟁점을 제시하고,
  마지막 문장은 반드시 "~에 대한 자신의 의견을 논리적으로 제시하는 글을 쓰시오." 형식으로 끝낼 것
- 특정 진영을 옹호하지 말고 중립적으로 쟁점만 제시할 것"""


def _generate_problem(keyword: str) -> GeneratedProblem:
    model = get_structured_model(GeneratedProblemOutput)

    def invoke(prompt: str) -> GeneratedProblemOutput:
        result = model.invoke([HumanMessage(content=prompt)])
        return result

    output = invoke_with_retry(
        invoke,
        _build_generation_prompt(keyword),
        operation_name="Recommend problem generation",
        max_attempts=MAX_ATTEMPTS,
    )
    return GeneratedProblem(title=output.title, content=output.content)


async def _run_recommend(request: RecommendRequest) -> RecommendResult:
    matches: list[RecommendedProblem] = (
        []
        if request.force_generate
        else await asyncio.to_thread(_hybrid_search, request.keyword)
    )
    if matches:
        return RecommendResult(matches=matches, generated=None)

    try:
        generated = await asyncio.to_thread(_generate_problem, request.keyword)
    except Exception as exc:
        logger.exception("Recommend problem generation failed")
        raise ValueError(
            f"추천 문제 생성 에이전트가 {MAX_ATTEMPTS}회 시도 후에도 실패했습니다: {exc}"
        ) from exc
    return RecommendResult(matches=[], generated=generated)


@observe(name="recommend:guardrail_input", as_type="span")
def guardrail_input_node(state: RecommendState) -> dict[str, object]:
    result = guardrails.check_input_safety(state.request.keyword)
    if result.flagged:
        return {"error": f"입력 검증에서 차단됨 ({result.category}): {result.reason}"}
    return {}


def _route_after_guardrail(state: RecommendState) -> str:
    return END if state.error else "recommend_agent"


@observe(name="recommend:recommend_agent", as_type="span")
async def recommend_agent_node(state: RecommendState) -> dict[str, object]:
    try:
        return {"result": await _run_recommend(state.request), "error": None}
    except Exception as exc:
        logger.exception("Recommend agent failed")
        return {"error": str(exc)}


def build_recommend_graph():
    graph = StateGraph(RecommendState)
    graph.add_node("guardrail_input", guardrail_input_node)
    graph.add_node("recommend_agent", recommend_agent_node)
    graph.add_edge(START, "guardrail_input")
    graph.add_conditional_edges(
        "guardrail_input",
        _route_after_guardrail,
        {"recommend_agent": "recommend_agent", END: END},
    )
    graph.add_edge("recommend_agent", END)
    return graph.compile()


recommend_app = build_recommend_graph()


async def run_recommend(request: RecommendRequest) -> RecommendResult:
    result_raw = await recommend_app.ainvoke(RecommendState(request=request))
    state = RecommendState.model_validate(result_raw)
    if state.error or state.result is None:
        raise ValueError(state.error or "추천 문제 생성 결과가 비어 있습니다.")
    return state.result
