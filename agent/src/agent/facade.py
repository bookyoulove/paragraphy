"""Paragraphy 에이전트 패키지의 공개 진입점.

그래프 구현과 상태/출력 스키마는 하위 모듈에 두고, 백엔드가 의존하는 공개 API는
여기서 작은 어댑터 클래스로 제공한다. 따라서 FastAPI 레이어는 LangGraph 상태의
내부 키를 알 필요가 없다.
"""

from __future__ import annotations

from typing import override

from shared.protocol import (
    AnalysisAgentProtocol,
    RubricAgentProtocol,
    TutorChatAgentProtocol,
)
from shared.schema.analysis import AnalysisRequest, AnalysisResult
from shared.schema.rubric import Rubric, RubricGenerationRequest, RubricList
from shared.schema.tutor import TutorChatInput, TutorChatOutput

from agent.graphs.grading import grading_app
from agent.graphs.rubric import rubric_app
from agent.graphs.tutor import tutor_chat_app
from agent.schemas.grading import AnalysisOutput, GradingState
from agent.schemas.rubric import RubricGenerationOutput, RubricState
from agent.schemas.tutor import TutorChatState


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
        result_raw = await rubric_app.ainvoke(RubricState(request=input))
        result = RubricState.model_validate(result_raw)
        if result.error:
            raise ValueError(result.error)
        return _to_backend_rubric_list(RubricGenerationOutput(rubrics=result.rubrics))


class AnalysisAgent(AnalysisAgentProtocol):
    """문제 객체를 채점 그래프 입력으로 변환하는 백엔드 어댑터."""

    @override
    async def run(self, input: AnalysisRequest) -> AnalysisResult:
        result_raw = await grading_app.ainvoke(GradingState(request=input))
        result = GradingState.model_validate(result_raw)
        if result.error:
            raise ValueError(result.error)
        return _to_backend_analysis_result(
            AnalysisOutput(
                grammar_result=result.grammar_result,
                criteria_scores=result.criteria_scores,
                overall_comment=result.overall_comment or None,
            )
        )


class TutorChatAgent(TutorChatAgentProtocol):
    """튜터링 그래프의 백엔드 어댑터."""

    @override
    async def run(self, input: TutorChatInput) -> TutorChatOutput:

        result_raw = await tutor_chat_app.ainvoke(TutorChatState(request=input))
        result = TutorChatState.model_validate(result_raw)
        return TutorChatOutput(
            reply=result.reply,
            error=result.error,
        )


__all__ = ["AnalysisAgent", "RubricAgent", "TutorChatAgent"]
