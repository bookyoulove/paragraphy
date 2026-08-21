"""Tutor Chat 그래프의 계약 모델."""

from pydantic import BaseModel
from shared.schema.tutor import TutorChatInput


class TutorChatState(BaseModel):
    request: TutorChatInput
    reply: str = ""
    error: str | None = None
    # 입력 가드레일 차단 여부 — error(모델/시스템 오류)와 구분해 WS 계층에서
    # 서로 다른 메시지 타입("blocked" vs "error")으로 내려보낼 수 있게 한다.
    blocked: bool = False
    block_reason: str = ""