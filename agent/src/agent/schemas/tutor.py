"""Tutor Chat 그래프의 계약 모델."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class TutorChatInput(BaseModel):
    context_text: str
    history: list[ChatMessage] = Field(default_factory=list)


class TutorChatOutput(BaseModel):
    reply: str
    error: str | None = None


class TutorChatState(BaseModel):
    request: TutorChatInput
    reply: str = ""
    error: str | None = None
