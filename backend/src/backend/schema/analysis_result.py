from uuid import UUID

from pydantic import BaseModel
from shared.schema.analysis import AnalysisResult as AnalysisResultBase
from shared.schema.grammar import GrammarResult

from backend.orm.models import CriteriaScore


class AnalysisResultCreate(AnalysisResultBase):
    answer_id: UUID


class AgentAnalysisResult(AnalysisResultBase): ...


class AnalysisResultUpdate(BaseModel):
    grammar_result: GrammarResult | None = None
    criteria_scores: list[CriteriaScore] | None = None
    overall_comment: str | None = None

class AnalysisResultPublic(AnalysisResultBase):
    id: UUID