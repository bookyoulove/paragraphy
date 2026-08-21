from uuid import UUID

from sqlmodel import col, select

from backend.orm.crud._base import CRUDBase
from backend.orm.models import UserSkillReports
from backend.schema.skill_report import UserSkillReportCreate


class CRUDUserSkillReport(
    CRUDBase[UserSkillReports, UserSkillReportCreate, UserSkillReportCreate]
):
    def get_by_user(self, user_id: UUID) -> list[UserSkillReports]:
        statement = (
            select(self.model)
            .where(col(self.model.user_id) == user_id)
            .order_by(col(self.model.period_end).desc())
        )
        return list(self.session.exec(statement).all())
