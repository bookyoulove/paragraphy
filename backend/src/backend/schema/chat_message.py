from uuid import UUID

from pydantic import BaseModel

from backend.orm.models import ChatMessageBase


class ChatMessageCreate(ChatMessageBase):
    chat_id: UUID


class ChatMessagePublic(ChatMessageBase): ...


class ChatMessageUpdate(BaseModel):
    role: str | None = None
    content: str | None = None
