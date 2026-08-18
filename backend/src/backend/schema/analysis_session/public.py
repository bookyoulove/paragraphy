from uuid import UUID

from backend.orm.models import AnalysisSessionBase


class AnalysisSessionPublic(AnalysisSessionBase):
    id: UUID
