"""DeepEval로 채점 모델·temperature·반복 횟수를 비교하는 로컬 벤치마크.

후보별로 별도 프로세스를 실행하므로 agent의 모델 캐시가 다른 후보에 재사용되지
않는다. API 키는 후보 설정에 직접 넣지 말고 `api_key_env`로 가리킨다.

빠른 샘플 실행:
    uv run --package agent --group dev python agent/scripts/evaluate_grading.py \
      --limit 12

전체 골든셋 실행:
    uv run --package agent --group dev python agent/scripts/evaluate_grading.py \
      --limit 0

결과 기본 저장 위치는 gitignore된 `dataset/deepeval-results.json`이다.
"""

from __future__ import annotations

import asyncio
import json
import os
import random
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, cast, override

import typer
from deepeval.evaluate import evaluate
from deepeval.evaluate.configs import AsyncConfig, CacheConfig, DisplayConfig
from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase
from dotenv import load_dotenv

DATASET_GLOB = "NIKL_GRADING WRITING DATA*/*.json"
DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "eval_models.json"
DEFAULT_OUTPUT = Path("dataset/deepeval-results.json")
CRITERIA = (
    ("con1", "내용 평가 준거 1"),
    ("con2", "내용 평가 준거 2"),
    ("con3", "내용 평가 준거 3"),
    ("con4", "내용 평가 준거 4"),
    ("con5", "내용 평가 준거 5"),
    ("exp1", "표현 평가 준거 1"),
    ("exp2", "표현 평가 준거 2"),
    ("org1", "구성 평가 준거 1"),
    ("org2", "구성 평가 준거 2"),
)


@dataclass(frozen=True)
class GoldCase:
    case_id: str
    prompt_group: str
    problem: str
    answer: str
    evaluator1: tuple[int, ...]
    evaluator2: tuple[int, ...]

    @property
    def consensus(self) -> tuple[float, ...]:
        return tuple(
            (left + right) / 2 for left, right in zip(self.evaluator1, self.evaluator2)
        )

    @property
    def evaluator_totals(self) -> tuple[int, int]:
        return sum(self.evaluator1), sum(self.evaluator2)


class NumericGradingMetric(BaseMetric):
    """구조화된 점수를 두 명의 사람 채점 결과와 비교하는 DeepEval metric."""

    threshold = 0.8
    async_mode = False
    verbose_mode = False

    metric_name = "NIKL grading agreement"

    @override
    def measure(self, test_case: LLMTestCase, *args: Any, **kwargs: Any) -> float:
        self.error = None
        try:
            actual = json.loads(test_case.actual_output or "")
            expected = json.loads(test_case.expected_output or "")
            actual_scores = [int(value) for value in actual["scores"]]
            consensus = [float(value) for value in expected["consensus"]]
            if len(actual_scores) != len(CRITERIA):
                raise ValueError("채점 항목 수가 9개가 아닙니다.")
            criterion_mae = sum(
                abs(actual_value - expected_value)
                for actual_value, expected_value in zip(actual_scores, consensus)
            ) / len(CRITERIA)
            score = max(0.0, 1.0 - criterion_mae / 5.0)
            self.score = score
            self.reason = f"consensus criterion MAE={criterion_mae:.3f}"
            return score
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            self.score = 0.0
            self.reason = f"invalid grading output: {exc}"
            self.error = str(exc)
            return 0.0

    @override
    async def a_measure(
        self, test_case: LLMTestCase, *args: Any, **kwargs: Any
    ) -> float:
        return self.measure(test_case, *args, **kwargs)


def _first_document(data: dict[str, Any]) -> dict[str, Any] | None:
    documents = data.get("document")
    if not isinstance(documents, list) or not documents:
        return None
    document = documents[0]
    return document if isinstance(document, dict) else None


def _score_vector(evaluation_data: dict[str, Any], evaluator: int) -> tuple[int, ...]:
    values: list[int] = []
    for category, count in (("con", 5), ("exp", 2), ("org", 2)):
        category_data = evaluation_data.get(f"eva_score_{category}", {})
        for index in range(1, count + 1):
            key = f"evaluator{evaluator}_score_{category}{index}"
            value = category_data.get(key)
            if not isinstance(value, int):
                raise TypeError(f"{key}가 정수가 아닙니다.")
            values.append(value)
    return tuple(values)


def _load_case(path: Path) -> GoldCase:
    with path.open(encoding="utf-8-sig") as file:
        data = json.load(file)
    document = _first_document(data)
    if document is None:
        raise ValueError("document가 없습니다.")
    metadata = document.get("metadata", {})
    prompt = metadata.get("prompt", {})
    problem = prompt.get("prompt_con")
    if not isinstance(problem, str):
        raise TypeError("prompt_con이 문자열이 아닙니다.")
    paragraphs = document.get("paragraph", [])
    answer = "".join(
        paragraph.get("form", "")
        for paragraph in paragraphs
        if isinstance(paragraph, dict) and isinstance(paragraph.get("form", ""), str)
    )
    evaluation_data = document.get("evaluation", {}).get("evaluation_data", {})
    evaluator1 = _score_vector(evaluation_data, 1)
    evaluator2 = _score_vector(evaluation_data, 2)
    case_id = str(data.get("id") or path.stem)
    return GoldCase(
        case_id=case_id,
        prompt_group=str(prompt.get("prompt_num") or "unknown"),
        problem=problem,
        answer=answer,
        evaluator1=evaluator1,
        evaluator2=evaluator2,
    )


def _select_cases(dataset_dir: Path, limit: int, seed: int) -> list[GoldCase]:
    paths = sorted(dataset_dir.glob(DATASET_GLOB))
    if not paths:
        raise FileNotFoundError(
            f"골든셋을 찾지 못했습니다: {dataset_dir / DATASET_GLOB}"
        )
    cases = [_load_case(path) for path in paths]
    if limit == 0 or limit >= len(cases):
        return cases

    random_generator = random.Random(seed)
    by_group: dict[str, list[GoldCase]] = {}
    for case in cases:
        by_group.setdefault(case.prompt_group, []).append(case)
    for group_cases in by_group.values():
        random_generator.shuffle(group_cases)

    selected: list[GoldCase] = []
    groups = sorted(by_group)
    while len(selected) < limit:
        added = False
        for group in groups:
            if by_group[group] and len(selected) < limit:
                selected.append(by_group[group].pop())
                added = True
        if not added:
            break
    return selected


def _rubric_payload() -> list[dict[str, str]]:
    return [
        {"criteria": criteria, "description": description}
        for criteria, description in CRITERIA
    ]


def _worker_input(cases: list[GoldCase]) -> list[dict[str, Any]]:
    return [
        {
            "case_id": case.case_id,
            "problem": case.problem,
            "answer": case.answer,
        }
        for case in cases
    ]


async def _run_worker(input_path: Path, output_path: Path) -> None:
    # Import after the parent has injected candidate-specific environment variables.
    from shared.schema.analysis import AnalysisRequest
    from shared.schema.problem import ProblemWithRubrics
    from shared.schema.rubric import Rubric

    from agent.graphs.grading import grading_agent_node, supervisor_node
    from agent.schemas.grading import CriterionScore, GradingState

    with input_path.open(encoding="utf-8") as file:
        cases = json.load(file)
    results: list[dict[str, Any]] = []
    for case in cases:
        started = time.perf_counter()
        try:
            request = AnalysisRequest(
                user_answer=case["answer"],
                problem=ProblemWithRubrics(
                    title=f"NIKL benchmark {case['case_id']}",
                    content=case["problem"],
                    model_answer=None,
                    rubrics=[Rubric(**rubric) for rubric in _rubric_payload()],
                ),
                user_identifier=f"deepeval-{case['case_id']}",
                session_id=case["case_id"],
            )
            state = GradingState(request=request)
            state = state.model_copy(update=supervisor_node(state))
            # 모델/temperature 비교에 집중하기 위해 맞춤법·가드레일·RAG는
            # 실행하지 않는다. 모든 실험 조합이 동일한 채점 prompt를 받는다.
            output = await grading_agent_node(state)
            if output.get("error"):
                raise RuntimeError(str(output["error"]))
            scores_value = output.get("criteria_scores", [])
            if not isinstance(scores_value, list) or not all(
                isinstance(score, CriterionScore) for score in scores_value
            ):
                raise TypeError("채점 결과의 항목 형식이 올바르지 않습니다.")
            scores = cast(list[CriterionScore], scores_value)
            results.append(
                {
                    "case_id": case["case_id"],
                    "scores": [score.score for score in scores],
                    "total": sum(score.score for score in scores),
                    "overall_comment": output.get("overall_comment", ""),
                    "latency_ms": round((time.perf_counter() - started) * 1000, 1),
                }
            )
        except Exception as exc:
            results.append(
                {
                    "case_id": case["case_id"],
                    "error": str(exc),
                    "latency_ms": round((time.perf_counter() - started) * 1000, 1),
                }
            )
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(results, file, ensure_ascii=False, indent=2)


def _candidate_environment(
    candidate: dict[str, Any], temperature: float | None, replicas: int
) -> dict[str, str]:
    environment = os.environ.copy()
    api_key_env = candidate.get("api_key_env", "AI_CLOUD_API_KEY")
    api_key = environment.get(api_key_env)
    if api_key:
        environment["AI_CLOUD_API_KEY"] = api_key
    environment["AI_CLOUD_MODEL"] = str(candidate["model"])
    environment["AI_CLOUD_BASE_URL"] = str(candidate["base_url"])
    environment["AI_CLOUD_GRADING_TEMPERATURE"] = (
        "" if temperature is None else str(temperature)
    )
    environment["AI_CLOUD_GRADING_REPLICAS"] = str(replicas)
    environment.pop("OPENAI_BASE_URL", None)
    environment.pop("OPENAI_MODEL", None)
    environment.pop("MODEL_NAME", None)
    environment.pop("RUBRIC_MODEL_NAME", None)
    return environment


def _load_candidates(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as file:
        candidates = json.load(file)
    if not isinstance(candidates, list):
        raise TypeError("후보 설정은 JSON 배열이어야 합니다.")
    return candidates


def _metric_cases(
    cases: list[GoldCase], results: list[dict[str, Any]]
) -> list[LLMTestCase]:
    by_id = {result["case_id"]: result for result in results}
    test_cases: list[LLMTestCase] = []
    for case in cases:
        result = by_id.get(case.case_id, {"error": "결과 없음"})
        test_cases.append(
            LLMTestCase(
                name=case.case_id,
                input=case.problem + "\n\n학생 답안:\n" + case.answer,
                actual_output=json.dumps(result, ensure_ascii=False),
                expected_output=json.dumps(
                    {
                        "evaluator1": case.evaluator1,
                        "evaluator2": case.evaluator2,
                        "consensus": case.consensus,
                    },
                    ensure_ascii=False,
                ),
            )
        )
    return test_cases


def _summary(cases: list[GoldCase], results: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = {result["case_id"]: result for result in results}
    valid = [result for result in results if isinstance(result.get("scores"), list)]
    criterion_errors: list[float] = []
    total_errors: list[float] = []
    within_one: list[bool] = []
    for case in cases:
        result = by_id.get(case.case_id, {})
        scores = result.get("scores")
        if not isinstance(scores, list) or len(scores) != len(CRITERIA):
            continue
        consensus = case.consensus
        criterion_errors.extend(
            abs(int(actual) - expected) for actual, expected in zip(scores, consensus)
        )
        total_errors.append(abs(sum(map(int, scores)) - sum(consensus)))
        within_one.append(
            all(
                abs(int(actual) - expected) <= 1
                for actual, expected in zip(scores, consensus)
            )
        )
    errors = [str(result["error"]) for result in results if result.get("error")]
    return {
        "cases": len(cases),
        "valid_outputs": len(valid),
        "error_count": len(errors),
        "error_examples": errors[:3],
        "validity_rate": len(valid) / len(cases) if cases else 0,
        "criterion_consensus_mae": sum(criterion_errors) / len(criterion_errors)
        if criterion_errors
        else None,
        "total_consensus_mae": sum(total_errors) / len(total_errors)
        if total_errors
        else None,
        "criterion_within_one_rate": sum(within_one) / len(within_one)
        if within_one
        else None,
        "mean_latency_ms": (
            sum(float(result.get("latency_ms", 0)) for result in results) / len(results)
            if results
            else None
        ),
    }


def _run_candidate(
    candidate: dict[str, Any],
    temperature: float | None,
    replicas: int,
    cases: list[GoldCase],
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="paragraphy-deepeval-") as directory:
        directory_path = Path(directory)
        input_path = directory_path / "cases.json"
        output_path = directory_path / "results.json"
        with input_path.open("w", encoding="utf-8") as file:
            json.dump(_worker_input(cases), file, ensure_ascii=False)
        command = [
            sys.executable,
            str(Path(__file__).resolve()),
            "--worker",
            "--input",
            str(input_path),
            "--output-worker",
            str(output_path),
        ]
        completed = subprocess.run(
            command,
            env=_candidate_environment(candidate, temperature, replicas),
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0 or not output_path.exists():
            diagnostic = (completed.stderr or completed.stdout).strip()
            raise RuntimeError(
                f"후보 실행 실패: {candidate['name']} (exit={completed.returncode})"
                + (f"\n{diagnostic[-4000:]}" if diagnostic else "")
            )
        with output_path.open(encoding="utf-8") as file:
            results = json.load(file)

    test_cases = _metric_cases(cases, results)
    metric = NumericGradingMetric()
    deepeval_result = evaluate(
        test_cases,
        [metric],
        async_config=AsyncConfig(run_async=False),
        display_config=DisplayConfig(
            show_indicator=False,
            print_results=False,
            inspect_after_run=False,
        ),
        cache_config=CacheConfig(write_cache=False),
    )
    summary = _summary(cases, results)
    summary["deepeval_test_cases"] = len(deepeval_result.test_results)
    return {
        "candidate": candidate["name"],
        "model": candidate["model"],
        "base_url": candidate["base_url"],
        "temperature": temperature,
        "replicas": replicas,
        "summary": summary,
    }


app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.command()
def main(
    config: Annotated[Path, typer.Option("--config")] = DEFAULT_CONFIG,
    dataset_dir: Annotated[Path, typer.Option("--dataset-dir")] = Path("dataset"),
    limit: Annotated[int, typer.Option("--limit", help="0이면 전체 데이터셋")] = 12,
    seed: Annotated[int, typer.Option("--seed")] = 42,
    candidate: Annotated[
        str | None, typer.Option("--candidate", help="특정 후보 name만 실행")
    ] = None,
    temperature: Annotated[
        str | None,
        typer.Option(
            "--temperature", help="실험 temperature를 하나로 고정; none이면 미전송"
        ),
    ] = None,
    replicas: Annotated[
        int | None, typer.Option("--replicas", help="실행 횟수를 하나로 고정")
    ] = None,
    output: Annotated[Path, typer.Option("--output")] = DEFAULT_OUTPUT,
    worker: Annotated[bool, typer.Option("--worker", hidden=True)] = False,
    input_path: Annotated[Path | None, typer.Option("--input", hidden=True)] = None,
    worker_output: Annotated[
        Path | None, typer.Option("--output-worker", hidden=True)
    ] = None,
) -> None:
    if worker:
        if input_path is None or worker_output is None:
            raise typer.BadParameter(
                "worker에는 --input과 --output-worker가 필요합니다."
            )
        asyncio.run(_run_worker(input_path, worker_output))
        return

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    cases = _select_cases(dataset_dir, limit, seed)
    candidates = _load_candidates(config)
    if candidate:
        candidates = [item for item in candidates if item.get("name") == candidate]
        if not candidates:
            raise typer.BadParameter(f"후보를 찾지 못했습니다: {candidate}")
    temperatures = None
    if temperature is not None:
        temperatures = [None if temperature.lower() == "none" else float(temperature)]
    results: list[dict[str, Any]] = []
    for item in candidates:
        if not item.get("base_url"):
            print(f"skip {item['name']}: base_url이 비어 있습니다.")
            continue
        candidate_temperatures = temperatures or item.get("temperatures", [None])
        candidate_replicas = [replicas] if replicas else item.get("replicas", [3])
        for current_temperature in candidate_temperatures:
            for current_replicas in candidate_replicas:
                print(
                    f"run {item['name']} temperature={current_temperature} replicas={current_replicas} "
                    f"cases={len(cases)}"
                )
                results.append(
                    _run_candidate(
                        item, current_temperature, int(current_replicas), cases
                    )
                )

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as file:
        json.dump(results, file, ensure_ascii=False, indent=2)
    print(f"saved {len(results)} experiments to {output}")


if __name__ == "__main__":
    app()
