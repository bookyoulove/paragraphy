from uuid import UUID

from backend.orm.models import UserSkillReportBase
from shared.schema.skill_report import SkillAssessment


class UserSkillReportCreate(UserSkillReportBase):
    user_id: UUID
    skill_scores: list[SkillAssessment]


class UserSkillReportPublic(UserSkillReportBase):
    id: UUID
    skill_scores: list[SkillAssessment]
