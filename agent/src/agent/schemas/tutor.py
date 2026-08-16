"""Tutor Chat 그래프의 계약 모델."""

from pydantic import BaseModel
from shared.schema.tutor import TutorChatInput


class TutorChatState(BaseModel):
    request: TutorChatInput
    reply: str = ""
    error: str | None = None
