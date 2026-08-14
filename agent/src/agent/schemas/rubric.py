"""루브릭 생성 그래프의 계약 모델."""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing_extensions import TypedDict


class RubricSuggestion(BaseModel):
    criteria: str
    description: str = ""
    max_score: int = 5


class RubricGenerationOutput(BaseModel):
    rubrics: list[RubricSuggestion] = Field(min_length=1)


class RubricGenerationInput(BaseModel):
    content: str
    model_answer: str | None = None


class RubricState(TypedDict, total=False):
    content: str
    model_answer: str | None
    rag_context: str
    rubrics: list[RubricSuggestion]
    error: str | None
