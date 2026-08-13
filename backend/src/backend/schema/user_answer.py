from uuid import UUID

from pydantic import BaseModel

from backend.orm.models import Status, UserAnswerBase
from backend.schema.analysis_result import AnalysisResultPublic


class UserAnswerCreate(UserAnswerBase):
    session_id: UUID


class UpdateUserAnswerRequest(UserAnswerBase): ...


class InsertUserAnswerRequest(UserAnswerBase): ...


class UserAnswerUpdate(BaseModel):
    user_answer: str | None = None
    status: Status | None = None


class UserAnswerPublicWithResult(UserAnswerBase):
    id: UUID
    analysis_result: AnalysisResultPublic | None = None
