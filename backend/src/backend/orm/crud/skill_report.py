from backend.orm.crud._base import CRUDBase
from backend.orm.models import UserSkillReports
from backend.schema.skill_report import UserSkillReportCreate


class CRUDUserSkillReport(
    CRUDBase[UserSkillReports, UserSkillReportCreate, UserSkillReportCreate]
): ...
