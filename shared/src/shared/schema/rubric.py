from pydantic import BaseModel
from sqlmodel import Field, SQLModel


class RubricGenerationRequest(BaseModel):
    content: str
    model_answer: str | None = None


class Rubric(SQLModel):
    criteria: str = Field(max_length=256)
    description: str | None = None
