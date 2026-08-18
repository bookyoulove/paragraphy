from uuid import UUID

from pydantic import BaseModel

from backend.orm.models import AnalysisSessionBase


class AnalysisSessionRequest(BaseModel):
    problem_id: UUID


class AnalysisSessionCreate(AnalysisSessionBase):
    user_id: UUID
    problem_id: UUID


class AnalysisSessionUpdate(BaseModel):
    pass
