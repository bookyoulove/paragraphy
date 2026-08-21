"""Paragraphy 에이전트 패키지의 공개 진입점.

그래프 구현과 상태/출력 스키마는 하위 모듈에 두고, 백엔드가 의존하는 공개 API는
여기서 작은 어댑터 클래스로 제공한다. 따라서 FastAPI 레이어는 LangGraph 상태의
내부 키를 알 필요가 없다.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import override

from langfuse import observe, propagate_attributes
from shared.protocol import (
    AnalysisAgentProtocol,
    RecommendAgentProtocol,
    RubricAgentProtocol,
    SkillReportAgentProtocol,
    TutorChatAgentProtocol,
)
from shared.schema.analysis import AnalysisRequest, AnalysisResult
from shared.schema.recommend import RecommendRequest, RecommendResult
from shared.schema.rubric import Rubric, RubricGenerationRequest, RubricList
from shared.schema.skill_report import WeeklySkillReportOutput, WeeklySkillReportRequest
from shared.schema.tutor import TutorChatInput, TutorChatOutput

from agent.graphs.grading import grading_app
from agent.graphs.recommend import run_recommend
from agent.graphs.rubric import rubric_app
from agent.graphs.skill_report import skill_report_app
from agent.graphs.tutor import tutor_chat_app
from agent.schemas.grading import AnalysisOutput, GradingState
from agent.schemas.rubric import RubricGenerationOutput, RubricState
from agent.schemas.skill_report import SkillReportState
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
    @observe(name="rubric-request")
    async def run(self, input: RubricGenerationRequest) -> RubricList:
        with propagate_attributes(
            user_id=input.user_identifier,
            trace_name="rubric-request",
            metadata={"agent": "rubric"},
        ):
            result_raw = await rubric_app.ainvoke(RubricState(request=input))
        result = RubricState.model_validate(result_raw)
        if result.error:
            raise ValueError(result.error)
        return _to_backend_rubric_list(RubricGenerationOutput(rubrics=result.rubrics))


class AnalysisAgent(AnalysisAgentProtocol):
    """문제 객체를 채점 그래프 입력으로 변환하는 백엔드 어댑터."""

    @override
    @observe(name="grading-request")
    async def run(self, input: AnalysisRequest) -> AnalysisResult:
        with propagate_attributes(
            user_id=input.user_identifier,
            session_id=input.session_id,
            trace_name="grading-request",
            metadata={"agent": "grading", "problem_title": input.problem.title},
        ):
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
    @observe(name="tutor-chat-request")
    async def run(self, input: TutorChatInput) -> TutorChatOutput:
        with propagate_attributes(
            user_id=input.user_identifier,
            session_id=input.session_id,
            trace_name="tutor-chat-request",
            metadata={"agent": "tutor_chat"},
        ):
            result_raw = await tutor_chat_app.ainvoke(TutorChatState(request=input))
        result = TutorChatState.model_validate(result_raw)
        # 스트리밍 WS 경로는 blocked/error를 별도 메시지 타입으로 구분해 보내지만,
        # 이 non-streaming 어댑터는 TutorChatOutput에 blocked 필드가 없으므로
        # 차단 사유를 error로 승격해 호출자가 조용히 빈 응답을 받지 않게 한다.
        return TutorChatOutput(
            reply=result.reply,
            error=f"입력 검증에서 차단됨 ({result.block_reason})"
            if result.blocked
            else result.error,
        )


@observe(name="tutor-chat-request", as_type="span")
async def stream_tutor_chat(
    input: TutorChatInput,
) -> AsyncIterator[tuple[str, object]]:
    """WS 라우트 전용 스트리밍 진입점.

    `TutorChatAgent.run()`(non-streaming)과 같은 그래프를 쓰지만, 조각을 실시간으로
    넘겨준다는 점이 다르다. `@observe()`는 async generator를 감지하면 함수가 끝까지
    소비될 때까지 span을 열어두므로(각 `__anext__()`를 보존된 컨텍스트에서 실행)
    `guardrail_input`/`chat_responder` 노드의 span과 LangChain 콜백이 이 span의
    자식으로 기록된다 — non-streaming 경로와 동일한 trace 구조를 얻는다.
    백엔드가 LangGraph 상태의 내부 키를 몰라도 되도록, "custom"(텍스트 조각)은
    ("chunk", str)로, "values"(최종 state 스냅샷)는 ("state", TutorChatState)로
    감싸 넘긴다.
    """
    with propagate_attributes(
        user_id=input.user_identifier,
        session_id=input.session_id,
        trace_name="tutor-chat-request",
        metadata={"agent": "tutor_chat", "streaming": True},
    ):
        async for mode, payload in tutor_chat_app.astream(
            TutorChatState(request=input), stream_mode=["custom", "values"]
        ):
            if mode == "custom":
                yield "chunk", payload
            elif mode == "values":
                yield "state", TutorChatState.model_validate(payload)


class RecommendAgent(RecommendAgentProtocol):
    """키워드 기반 문제 추천(하이브리드 RAG)의 백엔드 어댑터."""

    @override
    async def run(self, input: RecommendRequest) -> RecommendResult:
        return await run_recommend(input)


class SkillReportAgent(SkillReportAgentProtocol):
    """Persisted grading evidence를 주간 역량 리포트로 변환하는 어댑터."""

    @override
    async def run(self, input: WeeklySkillReportRequest) -> WeeklySkillReportOutput:
        result_raw = await skill_report_app.ainvoke(SkillReportState(request=input))
        result = SkillReportState.model_validate(result_raw)
        if result.error or result.report is None:
            raise ValueError(result.error or "주간 리포트 결과가 비어 있습니다.")
        return result.report


__all__ = [
    "AnalysisAgent",
    "RecommendAgent",
    "RubricAgent",
    "SkillReportAgent",
    "TutorChatAgent",
    "stream_tutor_chat",
]
