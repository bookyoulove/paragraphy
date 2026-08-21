from backend.orm.crud import (
    CRUDAnalysisResult,
    CRUDChatMessage,
    CRUDChatSession,
    CRUDUserAnswer,
)
from backend.orm.models import AnalysisSessions, UserAnswers


def delete_answer_cascade(
    answer: UserAnswers,
    analysis_result_db: CRUDAnalysisResult,
    chat_session_db: CRUDChatSession,
    chat_message_db: CRUDChatMessage,
    user_answer_db: CRUDUserAnswer,
):
    result = answer.analysis_result
    if result:
        if result.chat_session:
            for message in result.chat_session.chat_messages:
                chat_message_db.delete(message.id)
            chat_session_db.delete(result.chat_session.id)
        analysis_result_db.delete(result.id)
    user_answer_db.delete(answer.id)


def delete_session_cascade(
    session: AnalysisSessions,
    analysis_result_db: CRUDAnalysisResult,
    chat_session_db: CRUDChatSession,
    chat_message_db: CRUDChatMessage,
    user_answer_db: CRUDUserAnswer,
):
    for answer in list(session.user_answers):
        delete_answer_cascade(answer, analysis_result_db, chat_session_db, chat_message_db, user_answer_db)
