from datetime import datetime
from uuid import UUID

from backend.orm.models import AnalysisSessionBase


class AnalysisSessionPublic(AnalysisSessionBase):
    id: UUID
    created_at: datetime
