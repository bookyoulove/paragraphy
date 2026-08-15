"""논술 채점 그래프의 계약 모델."""

from __future__ import annotations

from pydantic import BaseModel, Field
from shared.schema.analysis import AnalysisRequest
from shared.schema.grammar import GrammarResult


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
    grammar_errors: list[GrammarError] = Field(default_factory=list)

class GrammarError(BaseModel):
    type: str
    before: str
    after: str
    note: str

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

    grammar_result: GrammarResult = Field(default_factory=_empty_grammar_result)
    criteria_scores: list[CriterionScore] = Field(default_factory=list)
    overall_comment: str | None = None


class GradingInput(BaseModel):
    problem_content: str
    model_answer: str | None = None
    rubric_items: list[RubricItem]
    user_answer: str
    university: str | None = None


class GradingState(BaseModel):
    request: AnalysisRequest
    grammar_result: GrammarResult = Field(default_factory=_empty_grammar_result)
    rubric_items: list[RubricItem] = Field(default_factory=list)
    rag_context: str = ""
    revised_text: str | None = None
    grammar_error: str | None = None
    criteria_scores: list[CriterionScore] = Field(default_factory=list)
    total_score: float = 0
    overall_comment: str = ""
    error: str | None = None
    policy_warning: str | None = None
