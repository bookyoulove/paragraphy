from pydantic import BaseModel
from sqlmodel import Field, SQLModel


class ChatMessage(SQLModel):
    role: str = Field(max_length=10)
    content: str


class TutorChatInput(BaseModel):
    context_text: str
    history: list[ChatMessage] = Field(default_factory=list)


class TutorChatOutput(BaseModel):
    reply: str
    error: str | None = None
