"""루브릭 생성 그래프의 계약 모델."""

from __future__ import annotations

from pydantic import BaseModel, Field
from shared.schema.rubric import RubricGenerationRequest


class RubricSuggestion(BaseModel):
    criteria: str
    description: str = ""
    max_score: int = 5


class RubricGenerationOutput(BaseModel):
    rubrics: list[RubricSuggestion] = Field(min_length=1)


class RubricState(BaseModel):
    request: RubricGenerationRequest
    rag_context: str = ""
    rubrics: list[RubricSuggestion] = Field(default_factory=list)
    error: str | None = None
