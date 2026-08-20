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
    ChatMessageDBDep,
    ChatSessionDBDep,
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
    RenameUserAnswerRequest,
    UpdateUserAnswerRequest,
    UserAnswerCreate,
    UserAnswerUpdate,
)
from backend.services.deletion import delete_answer_cascade, delete_session_cascade

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
    existing = analysis_session_db.get_by_user_and_problem(user_id, request.problem_id)
    if existing:
        return existing
    return analysis_session_db.create(
        AnalysisSessionCreate(user_id=user_id, problem_id=request.problem_id)
    )


class UpsertResult(BaseModel):
    answer_id: UUID
    name: str | None = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=ZoneInfo("Asia/Seoul"))
    )


class RenameResult(BaseModel):
    answer_id: UUID
    name: str


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

    update_fields = {"user_answer": req.user_answer, "status": req.status}
    if req.name and req.name.strip():
        update_fields["name"] = req.name.strip()
    updated = user_answer_db.update(answer_id, UserAnswerUpdate(**update_fields))
    assert updated is not None

    return UpsertResult(answer_id=answer_id, name=updated.name, created_at=updated.created_at)


@router.post("/{session_id}/answers")
def insert_session_answer(
    session_id: UUID,
    req: InsertUserAnswerRequest,
    user_answer_db: UserAnswerDBDep,
    session: ValidSessionDep,
) -> UpsertResult:
    round_no = len(session.user_answers) + 1
    name = req.name.strip() if req.name and req.name.strip() else f"{round_no}회차"
    new_answer = user_answer_db.create(
        UserAnswerCreate(
            session_id=session_id,
            user_answer=req.user_answer,
            status=req.status,
            name=name,
        )
    )
    return UpsertResult(
        answer_id=new_answer.id, name=new_answer.name, created_at=new_answer.created_at
    )


@router.patch("/{session_id}/answers/{answer_id}/name")
def rename_session_answer(
    session_id: UUID,
    answer_id: UUID,
    req: RenameUserAnswerRequest,
    user_answer_db: UserAnswerDBDep,
    session: ValidSessionDep,
) -> RenameResult:
    answer = user_answer_db.get(answer_id)
    if not answer or answer.session_id != session_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Answer not found.",
        )

    updated = user_answer_db.update(answer_id, UserAnswerUpdate(name=req.name))
    assert updated is not None
    return RenameResult(answer_id=answer_id, name=updated.name)


@router.delete("/{session_id}/answers/{answer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session_answer(
    session_id: UUID,
    answer_id: UUID,
    user_answer_db: UserAnswerDBDep,
    analysis_result_db: AnalysisResultDBDep,
    chat_session_db: ChatSessionDBDep,
    chat_message_db: ChatMessageDBDep,
    session: ValidSessionDep,
):
    answer = user_answer_db.get(answer_id)
    if not answer or answer.session_id != session_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Answer not found.",
        )

    delete_answer_cascade(answer, analysis_result_db, chat_session_db, chat_message_db, user_answer_db)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: UUID,
    user_answer_db: UserAnswerDBDep,
    analysis_result_db: AnalysisResultDBDep,
    chat_session_db: ChatSessionDBDep,
    chat_message_db: ChatMessageDBDep,
    analysis_session_db: AnalysisSessionDBDep,
    session: ValidSessionDep,
):
    delete_session_cascade(session, analysis_result_db, chat_session_db, chat_message_db, user_answer_db)
    analysis_session_db.delete(session_id)


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


@router.get("/", response_model=list[AnalysisSessionPublicWithProblemAnswer])
def get_session_list(user_id: UserUUIDDep, session_db: AnalysisSessionDBDep):
    return [
        AnalysisSessionPublicWithProblemAnswer.model_validate(session)
        for session in session_db.get_by_user(user_id)
    ]


@router.get("/{session_id}", response_model=AnalysisSessionPublicWithProblemAnswer)
def get_session(session_id: UUID, session: ValidSessionDep):
    return AnalysisSessionPublicWithProblemAnswer.model_validate(session)
