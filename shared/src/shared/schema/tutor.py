from pydantic import BaseModel
from sqlmodel import Field, SQLModel


class ChatMessage(SQLModel):
    role: str = Field(max_length=10)
    content: str


class TutorChatInput(BaseModel):
    context_text: str
    history: list[ChatMessage] = Field(default_factory=list)
    # Langfuse trace 메타데이터용 (선택, 관측 전용).
    user_identifier: str | None = None
    session_id: str | None = None


class TutorChatOutput(BaseModel):
    reply: str
    error: str | None = None
