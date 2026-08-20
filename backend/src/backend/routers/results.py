from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from shared.schema.tutor import TutorChatInput, TutorChatOutput
from sqlmodel import select

from backend.depends import (
    AnalysisResultDBDep,
    ChatMessageDBDep,
    ChatSessionDBDep,
    TutorChatAgentDep,
    UserUUIDDep,
)
from backend.orm.models import AnalysisResults, AnalysisSessions, Status, UserAnswers
from backend.schema.analysis_result.response import (
    AnalysisResultPublicWithProblemAnswer,
)
from backend.schema.chat_message.input import ChatMessageCreate
from backend.schema.chat_message.public import ChatMessagePublic
from backend.schema.chat_session.input import ChatSessionCreate
from backend.schema.problem.response import ProblemPublicWithRubrics
from backend.schema.user_answer.public import UserAnswerPublic

router = APIRouter(
    prefix="/results",
    tags=["results"],
)


class UserMessage(BaseModel):
    content: str


class ResultRanking(BaseModel):
    """A single answer's live rank among submitted answers to the same problem."""

    problem_id: UUID
    rank: int = Field(ge=1)
    attempt_count: int = Field(ge=1)
    percentile: float = Field(ge=0, le=100)
    score: float = Field(ge=1, le=5)
    score_scale: int = 5


def get_valid_result(
    result_id: UUID, user_id: UserUUIDDep, result_db: AnalysisResultDBDep
) -> AnalysisResults:
    result = result_db.get(result_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Result not found"
        )
    if result.user_answer.analysis_session.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to chat with this result",
        )
    return result


ValidResultDep = Annotated[AnalysisResults, Depends(get_valid_result)]


def _average_score(result: AnalysisResults) -> float:
    if not result.criteria_scores:
        raise ValueError("채점 항목 점수가 없습니다.")
    return sum(item.score for item in result.criteria_scores) / len(
        result.criteria_scores
    )


@router.get("/{result_id}/ranking", response_model=ResultRanking)
def get_result_ranking(
    result: ValidResultDep,
    result_db: AnalysisResultDBDep,
) -> ResultRanking:
    """Calculate a live rank without persisting a stale aggregate."""
    current_answer = result.user_answer
    if current_answer.status != Status.SUBMITTED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="제출 완료된 답안만 순위를 확인할 수 있습니다.",
        )

    problem_id = current_answer.analysis_session.problem_id
    statement = (
        select(AnalysisResults)
        .join(UserAnswers, AnalysisResults.answer_id == UserAnswers.id)
        .join(AnalysisSessions, UserAnswers.session_id == AnalysisSessions.id)
        .where(AnalysisSessions.problem_id == problem_id)
        .where(UserAnswers.status == Status.SUBMITTED)
    )
    attempts = [
        candidate
        for candidate in result_db.session.exec(statement).all()
        if candidate.criteria_scores
    ]
    if not attempts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="비교할 채점 결과가 없습니다.",
        )

    current_score = _average_score(result)
    higher_score_count = sum(
        _average_score(candidate) > current_score for candidate in attempts
    )
    attempt_count = len(attempts)
    rank = higher_score_count + 1  # 동점자는 같은 등수(competition ranking)다.
    percentile = (
        100.0
        if attempt_count == 1
        else round((attempt_count - rank) / (attempt_count - 1) * 100, 1)
    )
    return ResultRanking(
        problem_id=problem_id,
        rank=rank,
        attempt_count=attempt_count,
        percentile=percentile,
        score=round(current_score, 2),
    )


@router.post("/{result_id}/chat")
async def chat_with_tutor(
    result_id: UUID,
    message: UserMessage,
    result: ValidResultDep,
    chat_session_db: ChatSessionDBDep,
    chat_message_db: ChatMessageDBDep,
    chat_agent: TutorChatAgentDep,
) -> TutorChatOutput:
    if not result.chat_session:
        chat_session = chat_session_db.create(ChatSessionCreate(result_id=result_id))
    else:
        chat_session = result.chat_session

    chat_message_db.create(
        ChatMessageCreate(chat_id=chat_session.id, role="user", content=message.content)
    )

    history = chat_session.chat_messages
    problem = result.user_answer.analysis_session.problem
    user_answer = result.user_answer
    context = AnalysisResultPublicWithProblemAnswer(
            grammar_result=result.grammar_result,
            criteria_scores=result.criteria_scores,
            overall_comment=result.overall_comment,
            problem=ProblemPublicWithRubrics.model_validate(problem),
            user_answer=UserAnswerPublic.model_validate(user_answer),
        )

    ctx = context.model_dump_json()
    res = await chat_agent.run(TutorChatInput(context_text=ctx, history=history))

    chat_message_db.create(
        ChatMessageCreate(chat_id=chat_session.id, role="assistant", content=res.reply)
    )
    return res


@router.get("/{result_id}/chat", response_model=list[ChatMessagePublic])
async def retrive_chat(
    result_id: UUID,
    result: ValidResultDep,
):
    if not result.chat_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No chat session found"
        )

    history = result.chat_session.chat_messages
    return history
