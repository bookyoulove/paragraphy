from backend.schema.analysis_session.public import AnalysisSessionPublic
from backend.schema.problem.response import ProblemPublicWithRubrics
from backend.schema.user_answer.response import UserAnswerPublicWithResult


class AnalysisSessionPublicWithProblemAnswer(AnalysisSessionPublic):
    problem: ProblemPublicWithRubrics
    user_answers: list[UserAnswerPublicWithResult]
