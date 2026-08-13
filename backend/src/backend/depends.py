from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from shared.protocol import AnalysisAgentProtocol, RubricAgentProtocol

from backend.orm.crud import (
    CRUDAnalysisResult,
    CRUDAnalysisSession,
    CRUDChatMessage,
    CRUDChatSession,
    CRUDProblem,
    CRUDRubric,
    CRUDUser,
    CRUDUserAnswer,
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

AuthDep = Annotated[str, Depends(oauth2_scheme)]
UserDBDep = Annotated[CRUDUser, Depends()]
ProblemDBDep = Annotated[CRUDProblem, Depends()]
AnalysisSessionDBDep = Annotated[CRUDAnalysisSession, Depends()]
RubricDBDep = Annotated[CRUDRubric, Depends()]
UserAnswerDBDep = Annotated[CRUDUserAnswer, Depends()]
AnalysisResultDBDep = Annotated[CRUDAnalysisResult, Depends()]
ChatSessionDBDep = Annotated[CRUDChatSession, Depends()]
ChatMessageDBDep = Annotated[CRUDChatMessage, Depends()]


def get_current_user_id(user_db: UserDBDep, username: AuthDep):
    user_db_obj = user_db.get_name(username)
    if user_db_obj is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="username not exists in db"
        )
    return user_db_obj.id


UserUUIDDep = Annotated[UUID, Depends(get_current_user_id)]


def get_rubric_agent() -> RubricAgentProtocol: ...
def get_analysis_agent() -> AnalysisAgentProtocol: ...


RubricAgentDep = Annotated[RubricAgentProtocol, Depends(get_rubric_agent)]

AnalysisAgentDep = Annotated[AnalysisAgentProtocol, Depends(get_analysis_agent)]
