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
    # Langfuse trace 메타데이터용 (선택). 채점 로직에는 관여하지 않는다 —
    # 백엔드가 알고 있는 사용자/세션 식별자를 관측용으로만 실어 보낸다.
    user_identifier: str | None = None
    session_id: str | None = None
