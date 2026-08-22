"""Contracts for the weekly learning-skill report workflow."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field
from shared.schema.analysis import CriteriaScore


class GradedAnswerReview(BaseModel):
    """The persisted grading evidence supplied to the report agent."""

    answer_id: UUID
    graded_at: datetime
    criteria_scores: list[CriteriaScore]
    overall_comment: str | None = None


class WeeklySkillReportRequest(BaseModel):
    period_start: datetime
    period_end: datetime
    reviews: list[GradedAnswerReview] = Field(min_length=1)
    # 서버가 인증된 사용자 식별자를 주입하며, 관측 메타데이터에만 사용한다.
    user_identifier: str | None = None


class SkillAssessment(BaseModel):
    key: str
    score: int = Field(ge=0, le=5)
    rationale: str = Field(min_length=1)
    improvement: str = Field(min_length=1)


class WeeklySkillReportOutput(BaseModel):
    """LLM output that is persisted as one immutable report snapshot."""

    skill_scores: list[SkillAssessment] = Field(min_length=5, max_length=5)
    overall_skill_comment: str = Field(min_length=1)
    next_learning_goal: str = Field(min_length=1)
    recommended_actions: list[str] = Field(min_length=1, max_length=3)
