"""GET /api/sessions, GET /api/sessions/{id} — 과거 세션 목록/상세(초안 비교표용) 스키마."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SessionListItemOut(BaseModel):
    session_id: str
    problem_id: str
    problem_title: str
    university: str | None
    year: int | None
    created_at: datetime
    round_count: int
    latest_total_score: float | None
    latest_round_at: datetime | None


class CriterionScoreOut(BaseModel):
    criterion: str
    score: int
    max_score: int
    rationale: str
    improvement: str


class RoundOut(BaseModel):
    round: int
    answer_id: str
    user_answer: str
    submitted_at: datetime
    result_id: str | None
    criteria_scores: list[CriterionScoreOut] | None
    total_score: float | None
    overall_comment: str | None


class SessionDetailOut(BaseModel):
    session_id: str
    problem_id: str
    problem_title: str
    problem_content: str
    university: str | None
    year: int | None
    rounds: list[RoundOut]
