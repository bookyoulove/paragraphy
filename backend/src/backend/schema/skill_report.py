from datetime import datetime
from uuid import UUID

from shared.schema.skill_report import SkillAssessment

from backend.orm.models import UserSkillReportBase


class UserSkillReportCreate(UserSkillReportBase):
    user_id: UUID
    skill_scores: list[SkillAssessment]


class UserSkillReportPublic(UserSkillReportBase):
    id: UUID
    skill_scores: list[SkillAssessment]
    created_at: datetime
