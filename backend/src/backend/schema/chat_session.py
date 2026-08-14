from uuid import UUID

from pydantic import BaseModel

from backend.orm.models import ChatSessionBase


class ChatSessionCreate(ChatSessionBase):
    result_id: UUID


class ChatSessionUpdate(BaseModel): ...
