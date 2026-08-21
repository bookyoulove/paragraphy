"""LangGraph state for the weekly skill report agent."""

from pydantic import BaseModel
from shared.schema.skill_report import (
    WeeklySkillReportOutput,
    WeeklySkillReportRequest,
)


class SkillReportState(BaseModel):
    request: WeeklySkillReportRequest
    report: WeeklySkillReportOutput | None = None
    error: str | None = None
