from shared.schema.analysis import AnalysisResult as AnalysisResultBase

from backend.schema.problem.response import ProblemPublicWithRubrics
from backend.schema.user_answer.public import UserAnswerPublic


class AnalysisResultPublicWithProblemAnswer(AnalysisResultBase):
    problem: ProblemPublicWithRubrics
    user_answer: UserAnswerPublic
