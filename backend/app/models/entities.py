"""ORM 모델.

`설계문서/ERD.md`를 기준으로 한다 (컴포넌트 설계서 1절: "기술 수준 상충 시 ERD·시퀀스
다이어그램 우선"). ERD 대비 추가한 항목은 그 자리에 주석으로 사유를 남긴다.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(primary_key=True, default=_uuid)
    user_name: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=_now)

    problems: Mapped[list["Problem"]] = relationship(back_populates="user")
    sessions: Mapped[list["AnalysisSession"]] = relationship(back_populates="user")


class Problem(Base):
    """문제은행 문제 + 사용자 직접 입력 문제.

    ERD에는 출처를 나타내는 별도 컬럼이 없어, `university`를 provenance 라벨로도
    겸용한다 (국립국어원 문항은 university="국립국어원"). 대학 소속이 없는 국가기관
    출처를 별도 컬럼 없이 표현하기 위한 실용적 재사용이며, 대학 값 자체를 조회
    조건(1단계 seed 대상 구분)으로 그대로 쓸 수 있어 스키마 확장 없이 해결된다.
    """

    __tablename__ = "problems"

    problem_id: Mapped[str] = mapped_column(primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(Text)
    created_by_user: Mapped[bool] = mapped_column(default=False)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    university: Mapped[str | None] = mapped_column(Text, nullable=True)
    year: Mapped[int | None] = mapped_column(nullable=True)
    content: Mapped[str] = mapped_column(Text)
    model_answer: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User | None"] = relationship(back_populates="problems")
    rubrics: Mapped[list["Rubric"]] = relationship(back_populates="problem", cascade="all, delete-orphan")
    sessions: Mapped[list["AnalysisSession"]] = relationship(back_populates="problem")


class Rubric(Base):
    __tablename__ = "rubrics"

    rubric_id: Mapped[str] = mapped_column(primary_key=True, default=_uuid)
    problem_id: Mapped[str] = mapped_column(ForeignKey("problems.problem_id"))
    criteria: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # ERD엔 없으나 "채점 배점 표준 = 5점 만점제" 결정(ERD.md 11절 결정 이력)을
    # 코드 레벨에서 강제하기 위해 승인받아 추가한 컬럼. 문제별 항목 개수는 가변,
    # 항목별 배점만 5점으로 고정.
    max_score: Mapped[int] = mapped_column(default=5)

    problem: Mapped["Problem"] = relationship(back_populates="rubrics")


class AnalysisSession(Base):
    __tablename__ = "analysis_sessions"

    session_id: Mapped[str] = mapped_column(primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"))
    problem_id: Mapped[str] = mapped_column(ForeignKey("problems.problem_id"))
    created_at: Mapped[datetime] = mapped_column(default=_now)

    user: Mapped["User"] = relationship(back_populates="sessions")
    problem: Mapped["Problem"] = relationship(back_populates="sessions")
    answers: Mapped[list["UserAnswer"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class UserAnswer(Base):
    """답안 원문. 재채점 시 새 행 생성 (ERD.md 10절 #3).

    `created_at`은 ERD에 명시돼 있진 않지만, 같은 세션 내 여러 회차(초안 비교표
    로직에 필요)를 구분·정렬할 유일한 기준이라 최소한으로 추가했다.
    """

    __tablename__ = "user_answers"

    answer_id: Mapped[str] = mapped_column(primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("analysis_sessions.session_id"))
    user_answer: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="draft")  # "draft" | "submitted"
    created_at: Mapped[datetime] = mapped_column(default=_now)
    updated_at: Mapped[datetime] = mapped_column(default=_now, onupdate=_now)

    session: Mapped["AnalysisSession"] = relationship(back_populates="answers")
    result: Mapped["AnalysisResult | None"] = relationship(back_populates="answer", uselist=False)


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    result_id: Mapped[str] = mapped_column(primary_key=True, default=_uuid)
    answer_id: Mapped[str] = mapped_column(ForeignKey("user_answers.answer_id"), unique=True)
    scores: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    corrections: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    agent_results: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_now)

    answer: Mapped["UserAnswer"] = relationship(back_populates="result")
    chat_session: Mapped["ChatSession | None"] = relationship(back_populates="result", uselist=False)


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    chat_id: Mapped[str] = mapped_column(primary_key=True, default=_uuid)
    result_id: Mapped[str] = mapped_column(ForeignKey("analysis_results.result_id"), unique=True)
    created_at: Mapped[datetime] = mapped_column(default=_now)

    result: Mapped["AnalysisResult"] = relationship(back_populates="chat_session")
    messages: Mapped[list["ChatMessage"]] = relationship(back_populates="chat", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    message_id: Mapped[str] = mapped_column(primary_key=True, default=_uuid)
    chat_id: Mapped[str] = mapped_column(ForeignKey("chat_sessions.chat_id"))
    role: Mapped[str] = mapped_column(Text)  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=_now)

    chat: Mapped["ChatSession"] = relationship(back_populates="messages")