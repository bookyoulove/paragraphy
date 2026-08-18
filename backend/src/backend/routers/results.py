from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from shared.schema.tutor import TutorChatInput, TutorChatOutput

from backend.depends import (
    AnalysisResultDBDep,
    ChatMessageDBDep,
    ChatSessionDBDep,
    TutorChatAgentDep,
    UserUUIDDep,
)
from backend.orm.models import AnalysisResults
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
