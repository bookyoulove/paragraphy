"""POST /api/feedback 요청/응답 스키마."""

from __future__ import annotations

from pydantic import BaseModel, Field


class FeedbackRequest(BaseModel):
    essay_text: str = Field(..., min_length=1)
    # 있으면 해당 답안(UserAnswer)의 AnalysisResult.corrections에 결과를 병합 저장
    answer_id: str | None = None


class SpellingCorrectionOut(BaseModel):
    original: str
    revised: str
    category: str
    comment: str


class PolishSuggestionOut(BaseModel):
    original: str
    suggestion: str
    reason: str


class FeedbackResponse(BaseModel):
    origin: str
    revised_text: str
    spelling_corrections: list[SpellingCorrectionOut]
    spelling_error: str | None = None  # bareun 호출 실패 시에도 200으로 응답하고 여기에 사유를 남김
    polish_suggestions: list[PolishSuggestionOut]
    polish_error: str | None = None
    overall_comment: str
    saved_to_result_id: str | None = None
