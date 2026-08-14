"""논술 채점 그래프의 계약 모델."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field
from shared.schema.grammar import GrammarResult
from typing_extensions import TypedDict


class RubricItem(BaseModel):
    criteria: str
    description: str = ""
    max_score: int = 5


class CriterionScore(BaseModel):
    criterion: str
    score: int = Field(ge=1, le=5)
    max_score: int = 5
    rationale: str = ""
    improvement: str = ""


class GradingOutput(BaseModel):
    criteria_scores: list[CriterionScore] = Field(default_factory=list)
    total_score: float = 0
    overall_comment: str = ""
    grammar_errors: list[dict[str, Any]] = Field(default_factory=list)


def _empty_grammar_result() -> GrammarResult:
    return GrammarResult(
        origin="",
        revised="",
        revised_blocks=[],
        whitespace_cleanup_ranges=[],
        revised_sentences=[],
        helps={},
        language="ko",
        tokens_count=0,
    )


class AnalysisOutput(BaseModel):
    """백엔드가 저장/응답에 사용하는 채점 결과 계약."""

    # 맞춤법/문법 전용 그래프가 연결되기 전까지의 호환용 빈 결과다.
    grammar_result: GrammarResult = Field(default_factory=_empty_grammar_result)
    criteria_scores: list[CriterionScore] = Field(default_factory=list)
    overall_comment: str | None = None


class GradingInput(BaseModel):
    problem_content: str
    model_answer: str | None = None
    rubric_items: list[RubricItem]
    user_answer: str
    university: str | None = None


class GradingState(TypedDict, total=False):
    problem_content: str
    model_answer: str | None
    rubric_items: list[RubricItem]
    user_answer: str
    university: str | None
    rag_context: str
    criteria_scores: list[CriterionScore]
    total_score: float
    overall_comment: str
    grammar_errors: list[dict[str, Any]]
    error: str | None
    policy_warning: str | None
