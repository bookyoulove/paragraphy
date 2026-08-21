from uuid import UUID

from pydantic import BaseModel, Field
from shared.schema.problem import ProblemContent

from backend.orm.models import ProblemBase
from backend.schema.rubric.input import RubricDraft


class ProblemCreate(ProblemBase):
    user_id: UUID | None = None
    source_report_id: UUID | None = None


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
