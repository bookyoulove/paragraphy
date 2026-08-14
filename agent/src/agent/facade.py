"""Paragraphy 에이전트 패키지의 공개 진입점.

그래프 구현과 상태/출력 스키마는 하위 모듈에 두고, 백엔드가 의존하는 공개 API는
여기서 작은 어댑터 클래스로 제공한다. 따라서 FastAPI 레이어는 LangGraph 상태의
내부 키를 알 필요가 없다.
"""

from __future__ import annotations

from typing import Any, override

from shared.protocol import AnalysisAgentProtocol, RubricAgentProtocol
from shared.schema.analysis import AnalysisRequest, AnalysisResult
from shared.schema.rubric import Rubric, RubricGenerationRequest, RubricList

from agent.graphs.grading import grading_app
from agent.graphs.rubric import rubric_app
from agent.schemas.grading import AnalysisOutput
from agent.schemas.rubric import RubricGenerationOutput


def _value(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _to_backend_rubric_list(output: RubricGenerationOutput) -> RubricList:
    return RubricList(
        rubrics=[
            Rubric(criteria=item.criteria, description=item.description or None)
            for item in output.rubrics
        ]
    )


def _to_backend_analysis_result(output: AnalysisOutput) -> AnalysisResult:
    return AnalysisResult(
        grammar_result=output.grammar_result,
        criteria_scores=[
            score.model_dump(exclude={"max_score"}) for score in output.criteria_scores
        ],
        overall_comment=output.overall_comment,
    )


class RubricAgent(RubricAgentProtocol):
    """루브릭 초안 생성의 백엔드 어댑터."""

    @override
    async def run(self, input: RubricGenerationRequest) -> RubricList:
        state = {
            "content": _value(input, "content", ""),
            "model_answer": _value(input, "model_answer"),
        }
        result = await rubric_app.ainvoke(state)
        if result.get("error"):
            raise ValueError(result["error"])
        return _to_backend_rubric_list(
            RubricGenerationOutput(rubrics=result.get("rubrics", []))
        )


class AnalysisAgent(AnalysisAgentProtocol):
    """문제 객체를 채점 그래프 입력으로 변환하는 백엔드 어댑터."""

    @override
    async def run(self, input: AnalysisRequest) -> AnalysisResult:
        problem = _value(input, "problem", {})
        rubric_items = []
        for rubric in _value(problem, "rubrics", []) or []:
            rubric_items.append(
                {
                    "criteria": _value(rubric, "criteria", ""),
                    "description": _value(rubric, "description", "") or "",
                    "max_score": 5,
                }
            )

        state = {
            "problem_content": _value(problem, "content", ""),
            "model_answer": _value(problem, "model_answer"),
            "rubric_items": rubric_items,
            "user_answer": _value(input, "user_answer", ""),
            "university": _value(problem, "university"),
        }
        result = await grading_app.ainvoke(state)
        if result.get("error"):
            raise ValueError(result["error"])
        return _to_backend_analysis_result(
            AnalysisOutput(
                criteria_scores=result.get("criteria_scores", []),
                overall_comment=result.get("overall_comment") or None,
            )
        )


__all__ = ["AnalysisAgent", "RubricAgent"]
