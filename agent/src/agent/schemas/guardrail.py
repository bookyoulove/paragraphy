"""가드레일 노드가 반환하는 구조화 결과."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

SafetyCategory = Literal[
    "safe",
    "self_harm",
    "violence",
    "hate",
    "illegal",
    "prompt_injection",
    "unknown",
]


class InputSafetyResult(BaseModel):
    flagged: bool = False
    category: SafetyCategory = "safe"
    reason: str = ""


class DirectWritingResult(BaseModel):
    flagged: bool = False
    reason: str = ""
