from uuid import UUID

from sqlmodel import select

from backend.orm.crud._base import CRUDBase
from backend.orm.models import AnalysisSessions
from backend.schema.analysis_session import AnalysisSessionCreate, AnalysisSessionUpdate


class CRUDAnalysisSession(
    CRUDBase[AnalysisSessions, AnalysisSessionCreate, AnalysisSessionUpdate]
):
    def get_by_user(self, user_id: UUID) -> list[AnalysisSessions]:
        stmt = select(self.model).where(self.model.user_id == user_id)
        return list(self.session.exec(stmt).all())
