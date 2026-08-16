from uuid import UUID

from pydantic import BaseModel, Field
from shared.schema.problem import ProblemContent

from backend.orm.models import ProblemBase

from .rubric import RubricDraft, RubricPublic


class ProblemCreate(ProblemBase):
    user_id: UUID | None = None


class ProblemUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    model_answer: str | None = None


class Criteria(BaseModel):
    created_by_user: bool | None = None
    university: str | None = None
    year: int | None = None


class CustomProblemCreate(ProblemContent):
    rubrics: list[RubricDraft] = Field(min_length=1)


class ProblemPublic(ProblemBase):
    id: UUID


class ProblemPublicWithRubrics(ProblemPublic):
    rubrics: list[RubricPublic]
