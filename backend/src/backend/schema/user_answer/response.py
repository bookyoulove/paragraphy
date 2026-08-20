from backend.schema.analysis_result.public import AnalysisResultPublic
from backend.schema.user_answer.public import UserAnswerPublic


class UserAnswerPublicWithResult(UserAnswerPublic):
    analysis_result: AnalysisResultPublic | None = None
