from datetime import datetime
from enum import StrEnum
from typing import Any, override
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from pydantic import TypeAdapter
from sqlmodel import (
    JSON,
    Column,
    Field,
    Relationship,
    SQLModel,
    TypeDecorator,
)

from backend.schema.grammar import GrammarResult


class PydanticJSON[T](TypeDecorator[T]):
    impl = JSON
    cache_ok = True

    def __init__(self, target_type: type[T]):
        super().__init__()
        self.adapter = TypeAdapter(target_type)

    @override
    def process_bind_param(self, value: Any, dialect: Any) -> dict[str, Any] | None:
        if value is None:
            return None
        return self.adapter.dump_python(value, mode="json")

    @override
    def process_result_value(self, value: Any, dialect: Any) -> T | None:
        if value is None:
            return None
        return self.adapter.validate_python(value)


"""
USERS {
    uuid id PK
    text user_name
    datetime created_at
}
"""


class Users(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_name: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=ZoneInfo("Asia/Seoul"))
    )

    analysis_sessions: list[AnalysisSessions] = Relationship(back_populates="user")
    problems: list[Problems] = Relationship(back_populates="user")


"""
PROBLEMS {
    uuid id PK
    string title
    bool created_by_user
    uuid user_id FK "nullable"
    string university "nullable"
    int year "nullable"
    text content
    text model_answer "nullable"
}
"""


class Problems(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str = Field(max_length=256)
    created_by_user: bool
    user_id: UUID | None = Field(None, foreign_key="users.id")
    university: str | None = Field(None, max_length=32)
    year: int | None = None
    content: str
    model_answer: str | None = None

    user: Users | None = Relationship(back_populates="problems")
    rubrics: list[Rubrics] = Relationship(back_populates="problem")
    analysis_sessions: list[AnalysisSessions] = Relationship(back_populates="problem")


"""
RUBRICS {
    uuid id PK
    uuid problem_id FK
    string criteria
    text description "nullable"
}
"""


class Rubrics(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    problem_id: UUID = Field(foreign_key="problems.id")
    criteria: str = Field(max_length=256)
    description: str | None = None

    problem: Problems = Relationship(back_populates="rubrics")


"""
ANALYSIS_SESSIONS {
    uuid id PK
    uuid user_id FK
    uuid problem_id FK
    datetime created_at
}
"""


class AnalysisSessions(SQLModel, table=True):
    __tablename__ = "analysis_sessions"  # type: ignore
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id")
    problem_id: UUID = Field(foreign_key="problems.id")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=ZoneInfo("Asia/Seoul"))
    )

    user: Users = Relationship(back_populates="analysis_sessions")
    user_answers: list[UserAnswers] = Relationship(back_populates="analysis_session")
    problem: Problems = Relationship(back_populates="analysis_sessions")


"""
USER_ANSWERS {
    uuid id PK
    uuid session_id FK
    text user_answer
    string status
}
"""


class Status(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"


class UserAnswers(SQLModel, table=True):
    __tablename__ = "user_answers"  # type: ignore
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    session_id: UUID = Field(foreign_key="analysis_sessions.id")
    user_answer: str
    status: Status

    analysis_session: AnalysisSessions = Relationship(back_populates="user_answers")
    analysis_result: AnalysisResults | None = Relationship(back_populates="user_answer")


"""
ANALYSIS_RESULTS {
    uuid id PK
    uuid answer_id FK

    json grammar_result
    json criteria_scores
    text overall_comment

    datetime created_at
}
"""


class CriteriaScore(SQLModel):
    criterion: str
    score: int = Field(ge=1, le=5)
    rationale: str
    improvement: str


class AnalysisResults(SQLModel, table=True):
    __tablename__ = "analysis_results"  # type: ignore
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    answer_id: UUID = Field(foreign_key="user_answers.id")
    grammar_result: GrammarResult = Field(sa_column=Column(PydanticJSON(GrammarResult)))
    criteria_scores: list[CriteriaScore] = Field(
        sa_column=Column(PydanticJSON(list[CriteriaScore]))
    )
    overall_comment: str | None

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=ZoneInfo("Asia/Seoul"))
    )

    user_answer: UserAnswers = Relationship(back_populates="analysis_result")
    chat_session: ChatSessions | None = Relationship(back_populates="analysis_result")


"""
CHAT_SESSIONS {
    uuid id PK
    uuid result_id FK
    datetime created_at
}
"""


class ChatSessions(SQLModel, table=True):
    __tablename__ = "chat_sessions"  # type: ignore
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    result_id: UUID = Field(foreign_key="analysis_results.id")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=ZoneInfo("Asia/Seoul"))
    )

    analysis_result: AnalysisResults = Relationship(back_populates="chat_session")
    chat_messages: list[ChatMessages] = Relationship(back_populates="chat_session")


"""
CHAT_MESSAGES {
    uuid id PK
    uuid chat_id FK
    string role
    text content
    datetime created_at
}
"""


class ChatMessages(SQLModel, table=True):
    __tablename__ = "chat_messages"  # type: ignore
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    chat_id: UUID = Field(foreign_key="chat_sessions.id")
    role: str = Field(max_length=10)
    content: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=ZoneInfo("Asia/Seoul"))
    )

    chat_session: ChatSessions = Relationship(back_populates="chat_messages")
