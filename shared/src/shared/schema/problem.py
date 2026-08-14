from sqlmodel import Field, SQLModel

from shared.schema.rubric import Rubric


class ProblemContent(SQLModel):
    title: str = Field(max_length=256)
    content: str
    model_answer: str | None = None


class ProblemWithRubrics(ProblemContent):
    rubrics: list[Rubric] = Field(min_length=1)
