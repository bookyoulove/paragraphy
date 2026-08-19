from uuid import UUID

from shared.schema.analysis import AnalysisResult as AnalysisResultBase


class AnalysisResultPublic(AnalysisResultBase):
    id: UUID
