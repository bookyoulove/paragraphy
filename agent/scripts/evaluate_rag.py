"""Ragas로 키워드 기반 문제 추천의 hybrid RAG를 평가한다.

골든셋은 ``논술문서 텍스트/ragas goldenset.md``의 주제별 키워드와
제시문을 사용한다. 각 제시문은 현재 문제 코퍼스의 관련 문맥(reference context)으로
취급하며, 실제 검색 결과를 Ragas의 context precision/recall로 평가한다.

Ragas는 애플리케이션 실행 경로에 필요하지 않은 로컬 평가 도구다. Python 3.14에서
Ragas 0.4.x의 필수 의존성인 scikit-network이 소스 빌드를 시도하므로, 실행 환경에는
scikit-network을 요구하지 않는 Ragas 0.2.x를 설치한다.

실행 예시:
    uv run --package agent --group dev python agent/scripts/evaluate_rag.py
    uv run --package agent --group dev python agent/scripts/evaluate_rag.py --limit 2
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, Literal, cast, override

import typer
from shared.schema.recommend import RecommendedProblem

from agent.graphs.recommend import _hybrid_search, _keyword_scan
from agent.integrations.writing_prompts import load_items

DEFAULT_GOLDENSET = (
    Path(__file__).resolve().parents[2] / "논술문서 텍스트" / "ragas goldenset.md"
)
DEFAULT_OUTPUT = Path("dataset/ragas-results.json")

Strategy = Literal["hybrid", "keyword", "both"]


@dataclass(frozen=True)
class RagGoldenCase:
    case_id: str
    topic: str
    keywords: tuple[str, ...]
    reference_context: str

    @property
    def query(self) -> str:
        return ", ".join(self.keywords)


def _parse_goldenset(path: Path) -> list[RagGoldenCase]:
    text = path.read_text(encoding="utf-8")
    headings = list(re.finditer(r"(?m)^## (?!#)(.+?)\s*$", text))
    cases: list[RagGoldenCase] = []
    for index, heading in enumerate(headings, 1):
        topic = heading.group(1).strip()
        block_end = headings[index].start() if index < len(headings) else len(text)
        block = text[heading.end() : block_end]
        prompt_match = re.search(r"(?ms)^### 제시문\s*\n(.*)", block)
        if prompt_match is None:
            raise ValueError(f"제시문을 찾지 못했습니다: {topic}")
        reference_context = re.split(
            r"(?m)^---\s*$", prompt_match.group(1), maxsplit=1
        )[0].strip()
        if not reference_context:
            raise ValueError(f"제시문이 비어 있습니다: {topic}")
        keywords = tuple(
            keyword.strip() for keyword in topic.split(",") if keyword.strip()
        )
        if not keywords:
            raise ValueError(f"키워드가 비어 있습니다: {topic}")
        cases.append(
            RagGoldenCase(
                case_id=f"ragas-{index:02d}",
                topic=topic,
                keywords=keywords,
                reference_context=reference_context,
            )
        )
    if not cases:
        raise ValueError(f"골든셋에 주제가 없습니다: {path}")
    return cases


def _retrieve(
    case: RagGoldenCase, strategy: Literal["hybrid", "keyword"]
) -> list[RecommendedProblem]:
    """각 주제 키워드를 검색하고 결과를 하나의 추천 목록으로 합친다.

    골든셋의 heading은 여러 검색 키워드를 쉼표로 나열한 형식이다. 이를
    그대로 하나의 긴 문자열로 검색하면 키워드 기준선은 항상 실패하고,
    hybrid도 semantic 검색에만 의존하게 된다. 실제 키워드 기반 추천을
    평가하기 위해 키워드별 결과를 순서대로 합치되 같은 문항은 제거한다.
    """
    retrieved: list[RecommendedProblem] = []
    seen_labels: set[str] = set()
    for keyword in case.keywords:
        matches = (
            _hybrid_search(keyword) if strategy == "hybrid" else _keyword_scan(keyword)
        )
        for item in matches:
            if item.label in seen_labels:
                continue
            seen_labels.add(item.label)
            retrieved.append(item)
    return retrieved[:5]


def _context_rows(
    cases: list[RagGoldenCase], strategy: Literal["hybrid", "keyword"]
) -> tuple[list[dict[str, Any]], list[list[RecommendedProblem]]]:
    retrieved_by_case: list[list[RecommendedProblem]] = []
    rows: list[dict[str, Any]] = []
    for case in cases:
        retrieved = _retrieve(case, strategy)
        retrieved_by_case.append(retrieved)
        rows.append(
            {
                "user_input": case.query,
                "retrieved_contexts": [item.content for item in retrieved],
                "reference": case.reference_context,
            }
        )
    return rows, retrieved_by_case


def _prepare_ragas_import() -> None:
    """현재 LangChain community 패키지와 Ragas의 legacy import를 연결한다."""
    import sys
    import types

    try:
        import nest_asyncio
    except ImportError:
        pass
    else:
        # Ragas 0.2.15 applies nest_asyncio globally while importing its
        # executor. Its Python 3.14 patch path makes asyncio.current_task()
        # return None inside the executor's own tasks, so asyncio.wait_for
        # raises "Timeout should be used inside a task".
        def _skip_nest_asyncio(*args: Any, **kwargs: Any) -> None:
            return None

        nest_asyncio.apply = _skip_nest_asyncio

    module_name = "langchain_community.chat_models.vertexai"
    if module_name not in sys.modules:
        compatibility_module = types.ModuleType(module_name)
        # Ragas는 이 타입을 completion 지원 여부 확인에만 사용한다. 현재
        # LangChain community에서는 Vertex 통합이 별도 패키지로 이동했으므로,
        # OpenAI-compatible evaluator만 사용하는 이 스크립트에서는 placeholder로
        # legacy import를 만족시킨다.
        compatibility_module.__dict__["ChatVertexAI"] = type("ChatVertexAI", (), {})
        sys.modules[module_name] = compatibility_module


def _evaluator_llm() -> Any:
    """프로젝트 모델을 Ragas evaluator로 감싼다.

    Ragas 0.2.15의 메트릭 실행은 비동기지만, Python 3.14에서 LangChain의
    비동기 HTTP 호출 경로와 Ragas executor의 timeout 처리가 충돌할 수 있다.
    실제 모델 호출만 동기 API를 작업 스레드에서 실행하면 Ragas의 메트릭 병렬성은
    유지하면서 Windows와 Linux에서 같은 event loop 동작을 보장할 수 있다.
    """
    _prepare_ragas_import()
    try:
        from ragas.llms import LangchainLLMWrapper
    except ImportError:
        from ragas.llms.base import LangchainLLMWrapper

    from agent.model import get_chat_model

    class _ThreadedSyncLangchainLLM(LangchainLLMWrapper):
        @override
        def generate_text(
            self,
            prompt: Any,
            n: int = 1,
            temperature: float = 1e-8,
            stop: list[str] | None = None,
            callbacks: Any = None,
        ) -> Any:
            # get_chat_model() returns a RunnableBinding because Langfuse callbacks
            # are attached with with_config(). Ragas 0.2.15 tries to assign
            # ``temperature`` on that binding, which Pydantic rejects. The
            # evaluator's configured model temperature is intentionally kept as-is.
            result = self.langchain_llm.generate_prompt(
                prompts=[prompt] * n,
                stop=stop,
                callbacks=callbacks,
            )
            if n > 1:
                result.generations = [
                    [generation[0] for generation in result.generations]
                ]
            return result

        @override
        async def agenerate_text(
            self,
            prompt: Any,
            n: int = 1,
            temperature: float | None = None,
            stop: list[str] | None = None,
            callbacks: Any = None,
        ) -> Any:
            return await asyncio.to_thread(
                self.generate_text,
                prompt=prompt,
                n=n,
                temperature=temperature,
                stop=stop,
                callbacks=callbacks,
            )

    return _ThreadedSyncLangchainLLM(cast(Any, get_chat_model()))


def _evaluate_strategy(
    cases: list[RagGoldenCase], strategy: Literal["hybrid", "keyword"]
) -> dict[str, Any]:
    _prepare_ragas_import()
    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import context_precision, context_recall
    except ImportError as exc:
        raise RuntimeError(
            "Ragas 평가를 실행하려면 `uv add --package agent --dev "
            '"ragas>=0.2.15,<0.3"`로 Ragas 0.2.x를 설치하세요.'
        ) from exc

    rows, retrieved_by_case = _context_rows(cases, strategy)
    result = evaluate(
        Dataset.from_list(rows),
        metrics=[context_precision, context_recall],
        llm=_evaluator_llm(),
        # 실패한 metric을 NaN으로 바꿔 저장하면 잘못된 평가 결과처럼 보이므로
        # benchmark에서는 첫 오류를 그대로 노출한다.
        raise_exceptions=True,
    )
    result_frame = result.to_pandas()
    metric_names = ("context_precision", "context_recall")
    summary = {
        name: result_frame[name].mean()
        if name in result_frame and not result_frame[name].isna().all()
        else None
        for name in metric_names
    }
    corpus_items = load_items()
    case_results: list[dict[str, Any]] = []
    for index, case in enumerate(cases):
        expected_labels = [
            str(item["label"])
            for item in corpus_items
            if item.get("content") == case.reference_context
        ]
        retrieved_labels = [item.label for item in retrieved_by_case[index]]
        scores = {
            name: (
                None
                if name not in result_frame
                or result_frame.iloc[index][name] != result_frame.iloc[index][name]
                else float(result_frame.iloc[index][name])
            )
            for name in metric_names
        }
        retrieved_expected_labels = [
            label for label in expected_labels if label in retrieved_labels
        ]
        case_results.append(
            {
                "case_id": case.case_id,
                "topic": case.topic,
                "query": case.query,
                "keyword_queries": list(case.keywords),
                "expected_labels": expected_labels,
                "retrieved_labels": retrieved_labels,
                "retrieved_expected_labels": retrieved_expected_labels,
                "scores": scores,
            }
        )
    summary["retrieval_hit_rate"] = sum(
        bool(case["retrieved_expected_labels"]) for case in case_results
    ) / len(case_results)
    return {"summary": summary, "cases": case_results}


app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.command()
def main(
    goldenset: Annotated[Path, typer.Option("--goldenset")] = DEFAULT_GOLDENSET,
    output: Annotated[Path, typer.Option("--output")] = DEFAULT_OUTPUT,
    limit: Annotated[int, typer.Option("--limit", help="0이면 전체 골든셋")] = 0,
    strategy: Annotated[
        Strategy,
        typer.Option("--strategy", help="hybrid, keyword, both 중 하나"),
    ] = "both",
) -> None:
    cases = _parse_goldenset(goldenset)
    if limit < 0:
        raise typer.BadParameter("limit은 0 이상이어야 합니다.")
    if limit:
        cases = cases[:limit]
    if not cases:
        raise typer.BadParameter("평가할 골든셋 케이스가 없습니다.")

    strategies: tuple[Literal["hybrid", "keyword"], ...] = (
        ("hybrid", "keyword") if strategy == "both" else (strategy,)
    )
    results: dict[str, Any] = {
        "goldenset": str(goldenset),
        "case_count": len(cases),
        "metrics": ["context_precision", "context_recall"],
        "strategies": {},
    }
    for current_strategy in strategies:
        print(f"evaluate {current_strategy}: cases={len(cases)}")
        results["strategies"][current_strategy] = _evaluate_strategy(
            cases, current_strategy
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"saved Ragas results to {output}")


if __name__ == "__main__":
    app()
