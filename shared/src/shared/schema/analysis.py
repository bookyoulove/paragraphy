from pydantic import BaseModel, Field
from shared.schema.grammar import GrammarResult
from shared.schema.problem import ProblemWithRubrics
from sqlmodel import SQLModel


class CriteriaScore(BaseModel):
    criterion: str
    score: int = Field(ge=1, le=5)
    rationale: str
    improvement: str


class AnalysisResult(SQLModel):
    grammar_result: GrammarResult
    criteria_scores: list[CriteriaScore]
    overall_comment: str | None


class AnalysisRequest(BaseModel):
    user_answer: str
    problem: ProblemWithRubrics
