from datetime import datetime
from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from shared.schema.analysis import AnalysisRequest

from backend.depends import (
    AnalysisAgentDep,
    AnalysisResultDBDep,
    AnalysisSessionDBDep,
    UserAnswerDBDep,
    UserUUIDDep,
)
from backend.orm.models import AnalysisSessions
from backend.schema.analysis_result.input import (
    AnalysisResultCreate,
    AnalysisResultUpdate,
)
from backend.schema.analysis_result.public import AnalysisResultPublic
from backend.schema.analysis_session.input import (
    AnalysisSessionCreate,
    AnalysisSessionRequest,
)
from backend.schema.analysis_session.response import (
    AnalysisSessionPublicWithProblem,
    AnalysisSessionPublicWithProblemAnswer,
)
from backend.schema.user_answer.input import (
    InsertUserAnswerRequest,
    UpdateUserAnswerRequest,
    UserAnswerCreate,
    UserAnswerUpdate,
)

router = APIRouter(
    prefix="/sessions",
    tags=["sessions"],
)


def valid_user_session(
    session_id: UUID, user_id: UserUUIDDep, analysis_session_db: AnalysisSessionDBDep
):
    session = analysis_session_db.get(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found.",
        )
    if session.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to access this session.",
        )
    return session


ValidSessionDep = Annotated[AnalysisSessions, Depends(valid_user_session)]


class ProblemListQuery(BaseModel):
    user_id: UUID
    created_by_user: bool | None


@router.post("/", response_model=AnalysisSessionPublicWithProblem)
def create_session(
    user_id: UserUUIDDep,
    request: AnalysisSessionRequest,
    analysis_session_db: AnalysisSessionDBDep,
):
    return analysis_session_db.create(
        AnalysisSessionCreate(user_id=user_id, problem_id=request.problem_id)
    )


class UpsertResult(BaseModel):
    answer_id: UUID
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=ZoneInfo("Asia/Seoul"))
    )


@router.put("/{session_id}/answers/{answer_id}")
def update_session_answer(
    session_id: UUID,
    answer_id: UUID,
    req: UpdateUserAnswerRequest,
    user_answer_db: UserAnswerDBDep,
    session: ValidSessionDep,
) -> UpsertResult:
    answer = user_answer_db.get(answer_id)
    if not answer or answer.session_id != session_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Answer not found.",
        )

    user_answer_db.update(
        answer_id, UserAnswerUpdate(user_answer=req.user_answer, status=req.status)
    )

    return UpsertResult(answer_id=answer_id)


@router.post("/{session_id}/answers")
def insert_session_answer(
    session_id: UUID,
    req: InsertUserAnswerRequest,
    user_answer_db: UserAnswerDBDep,
    session: ValidSessionDep,
) -> UpsertResult:
    new_answer = user_answer_db.create(
        UserAnswerCreate(
            session_id=session_id,
            user_answer=req.user_answer,
            status=req.status,
        )
    )
    return UpsertResult(answer_id=new_answer.id)


@router.get("/{session_id}/answers/{answer_id}/grading")
async def analysis_answer(
    session_id: UUID,
    answer_id: UUID,
    session: ValidSessionDep,
    user_answer_db: UserAnswerDBDep,
    analysis_result_db: AnalysisResultDBDep,
    agent: AnalysisAgentDep,
) -> AnalysisResultPublic:
    user_answer = user_answer_db.get(answer_id)
    if not user_answer or user_answer.session_id != session_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Answer not found.",
        )
    res = await agent.run(
        AnalysisRequest(user_answer=user_answer.user_answer, problem=session.problem)
    )

    if user_answer.analysis_result:
        analysis_result_db.update(
            user_answer.analysis_result.id,
            AnalysisResultUpdate(
                **res.model_dump(),
            ),
        )
        return user_answer.analysis_result
    res_db = analysis_result_db.create(
        AnalysisResultCreate(
            answer_id=answer_id,
            **res.model_dump(),
        )
    )
    return res_db


@router.get("/", response_model=list[AnalysisSessionPublicWithProblem])
def get_session_list(user_id: UserUUIDDep, session_db: AnalysisSessionDBDep):
    return session_db.get_by_user(user_id)


@router.get("/{session_id}", response_model=AnalysisSessionPublicWithProblemAnswer)
def get_session(session_id: UUID, session: ValidSessionDep):
    return session
