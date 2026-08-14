from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from shared.schema.analysis import AnalysisResult
from shared.schema.tutor import TutorChatInput, TutorChatOutput

from backend.depends import (
    AnalysisResultDBDep,
    ChatMessageDBDep,
    ChatSessionDBDep,
    TutorChatAgentDep,
    UserUUIDDep,
)
from backend.schema.chat_message import ChatMessageCreate
from backend.schema.chat_session import ChatSessionCreate

router = APIRouter(
    prefix="/results",
    tags=["results"],
)


class UserMessage(BaseModel):
    content: str


@router.post("/{result_id}/chat")
async def chat_with_tutor(
    result_id: UUID,
    message: UserMessage,
    user_id: UserUUIDDep,
    result_db: AnalysisResultDBDep,
    chat_session_db: ChatSessionDBDep,
    chat_message_db: ChatMessageDBDep,
    chat_agent: TutorChatAgentDep,
) -> TutorChatOutput:
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
    if not result.chat_session:
        chat_session = chat_session_db.create(ChatSessionCreate(result_id=result_id))
    else:
        chat_session = result.chat_session

    chat_message_db.create(
        ChatMessageCreate(chat_id=chat_session.id, role="user", content=message.content)
    )

    history = chat_session.chat_messages
    ctx = AnalysisResult.model_validate(result).model_dump_json()
    res = await chat_agent.run(TutorChatInput(context_text=ctx, history=history))

    chat_message_db.create(
        ChatMessageCreate(chat_id=chat_session.id, role="assistant", content=res.reply)
    )
    return res
