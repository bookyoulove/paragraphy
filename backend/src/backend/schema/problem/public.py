from uuid import UUID

from backend.orm.models import ProblemBase


class ProblemPublic(ProblemBase):
    id: UUID
    source_report_id: UUID | None = None
