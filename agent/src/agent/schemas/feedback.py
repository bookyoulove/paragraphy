"""문법/표현 첨삭 그래프의 계약 모델."""

from __future__ import annotations

from pydantic import BaseModel, Field
from shared.schema.grammar import GrammarResult
from typing_extensions import TypedDict


class SpellingCorrection(BaseModel):
    original: str
    revised: str
    category: str
    comment: str


class PolishSuggestion(BaseModel):
    original: str
    suggestion: str
    reason: str


class PolishOutput(BaseModel):
    polish_suggestions: list[PolishSuggestion] = Field(default_factory=list)
    overall_comment: str = ""


class FeedbackInput(BaseModel):
    essay_text: str


class FeedbackOutput(BaseModel):
    grammar_result: GrammarResult | None = None
    revised_text: str
    spelling_corrections: list[SpellingCorrection] = Field(default_factory=list)
    spelling_error: str | None = None
    polish_suggestions: list[PolishSuggestion] = Field(default_factory=list)
    overall_comment: str = ""
    error: str | None = None


class FeedbackState(TypedDict, total=False):
    essay_text: str
    grammar_result: GrammarResult
    revised_text: str
    spelling_corrections: list[SpellingCorrection]
    spelling_error: str | None
    polish_suggestions: list[PolishSuggestion]
    overall_comment: str
    error: str | None
