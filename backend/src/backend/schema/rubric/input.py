from uuid import UUID

from pydantic import BaseModel
from shared.schema.rubric import Rubric as RubricBase


class RubricCreate(RubricBase):
    problem_id: UUID


class RubricUpdate(BaseModel):
    criteria: str | None = None
    description: str | None = None


class RubricDraft(RubricBase): ...
