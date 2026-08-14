"""Tutor Chat 그래프의 계약 모델."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel
from typing_extensions import TypedDict


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class TutorChatInput(BaseModel):
    context_text: str
    history: list[ChatMessage]


class TutorChatOutput(BaseModel):
    reply: str
    error: str | None = None


class TutorChatState(TypedDict, total=False):
    context_text: str
    history: list[ChatMessage]
    reply: str
    error: str | None
