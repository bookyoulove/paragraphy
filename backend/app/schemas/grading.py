"""POST /api/grading 요청/응답 스키마."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class RubricItemIn(BaseModel):
    criteria: str
    description: str | None = None
    max_score: int = 5  # 정책상 5점 고정이지만 필드는 유지 (요청 검증용)


class GradingRequest(BaseModel):
    # 인증 미도입(컴포넌트 설계서 7절) — 식별자만으로 사용자 구분, 없으면 자동 등록
    user_identifier: str = Field(..., min_length=1)

    # 문제은행 문제 사용 시
    problem_id: str | None = None

    # 사용자 직접 입력 문제 사용 시 (둘 다 필수 — "채점기준 입력 필수" 정책)
    problem_content: str | None = None
    rubric_items: list[RubricItemIn] | None = None
    model_answer: str | None = None

    # 같은 세션에서 재채점(2차 이상)하려면 이전 세션 id를 전달
    session_id: str | None = None

    user_answer: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def _check_problem_source(self) -> "GradingRequest":
        if self.problem_id:
            return self
        if not self.problem_content or not self.rubric_items:
            raise ValueError(
                "problem_id가 없으면 problem_content와 rubric_items(채점기준)가 모두 필요합니다. "
                "사용자 직접 입력 문제는 채점기준 입력이 필수입니다."
            )
        return self


class CriterionScoreOut(BaseModel):
    criterion: str
    score: int
    max_score: int
    rationale: str
    improvement: str


class CriterionDeltaOut(BaseModel):
    criterion: str
    previous_score: int
    current_score: int
    delta: int


class PreviousComparisonOut(BaseModel):
    previous_round: int
    previous_total_score: float
    current_total_score: float
    total_delta: float
    per_criterion: list[CriterionDeltaOut]


class GradingResponse(BaseModel):
    session_id: str
    answer_id: str
    result_id: str
    problem_id: str
    round: int
    criteria_scores: list[CriterionScoreOut]
    total_score: float
    overall_comment: str
    previous_comparison: PreviousComparisonOut | None = None
    policy_warning: str | None = None  # 검증 에이전트가 "직접 첨삭" 의심 시 세팅 (soft flag)
