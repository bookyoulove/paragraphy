"""GET /api/problems, GET /api/problems/{id}, POST /api/problems/rubric 스키마."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ProblemListItemOut(BaseModel):
    problem_id: str
    title: str
    university: str | None
    year: int | None
    created_by_user: bool


class RubricOut(BaseModel):
    rubric_id: str
    criteria: str
    description: str | None
    max_score: int


class ProblemDetailOut(BaseModel):
    problem_id: str
    title: str
    content: str
    model_answer: str | None
    university: str | None
    year: int | None
    created_by_user: bool
    rubrics: list[RubricOut]


class RubricSuggestRequest(BaseModel):
    content: str = Field(..., min_length=1)
    model_answer: str | None = None


class RubricSuggestionOut(BaseModel):
    criteria: str
    description: str
    max_score: int = 5


class RubricSuggestResponse(BaseModel):
    rubrics: list[RubricSuggestionOut]
    error: str | None = None
