from datetime import datetime
from uuid import UUID

from sqlmodel import col, select

from backend.orm.crud._base import CRUDBase
from backend.orm.models import AnalysisResults, AnalysisSessions, UserAnswers
from backend.schema.analysis_result.input import (
    AnalysisResultCreate,
    AnalysisResultUpdate,
)


class CRUDAnalysisResult(
    CRUDBase[AnalysisResults, AnalysisResultCreate, AnalysisResultUpdate]
):
    def get_by_problem(self, problem_id: UUID) -> list[AnalysisResults]:
        statement = (
            select(self.model)
            .join(UserAnswers, col(self.model.answer_id) == col(UserAnswers.id))
            .join(
                AnalysisSessions,
                col(UserAnswers.session_id) == col(AnalysisSessions.id),
            )
            .where(col(AnalysisSessions.problem_id) == problem_id)
        )
        return list(self.session.exec(statement).all())

    def get_by_user_and_period(
        self, user_id: UUID, period_start: datetime, period_end: datetime
    ) -> list[AnalysisResults]:
        statement = (
            select(self.model)
            .join(UserAnswers, col(self.model.answer_id) == col(UserAnswers.id))
            .join(
                AnalysisSessions,
                col(UserAnswers.session_id) == col(AnalysisSessions.id),
            )
            .where(col(AnalysisSessions.user_id) == user_id)
            .where(col(self.model.created_at) >= period_start)
            .where(col(self.model.created_at) <= period_end)
            .order_by(col(self.model.created_at).asc())
        )
        return list(self.session.exec(statement).all())
