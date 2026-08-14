from uuid import UUID

from pydantic import BaseModel

from backend.orm.models import AnalysisSessionBase
from backend.schema.problem import ProblemPublicWithRubrics
from backend.schema.user_answer import UserAnswerPublicWithResult


class AnalysisSessionRequest(BaseModel):
    problem_id: UUID


class AnalysisSessionCreate(AnalysisSessionBase):
    user_id: UUID
    problem_id: UUID


class AnalysisSessionUpdate(BaseModel):
    pass


class AnalysisSessionPublic(AnalysisSessionBase):
    id: UUID


class AnalysisSessionPublicWithProblem(AnalysisSessionPublic):
    problem: ProblemPublicWithRubrics


class AnalysisSessionPublicWithProblemAnswer(AnalysisSessionPublic):
    problem: ProblemPublicWithRubrics
    user_answers: list[UserAnswerPublicWithResult]
