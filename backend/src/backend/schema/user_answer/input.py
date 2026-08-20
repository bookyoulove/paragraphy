from uuid import UUID

from pydantic import BaseModel, Field

from backend.orm.models import Status, UserAnswerBase


class UserAnswerCreate(UserAnswerBase):
    session_id: UUID


class UpdateUserAnswerRequest(BaseModel):
    user_answer: str
    status: Status
    name: str | None = None


class InsertUserAnswerRequest(BaseModel):
    user_answer: str
    status: Status
    name: str | None = None


class RenameUserAnswerRequest(BaseModel):
    name: str = Field(min_length=1, max_length=50)


class UserAnswerUpdate(BaseModel):
    user_answer: str | None = None
    status: Status | None = None
    name: str | None = None
