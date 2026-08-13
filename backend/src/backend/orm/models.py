from datetime import datetime
from enum import StrEnum
from typing import Any, Optional, override
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


class TimeStampMixin(SQLModel):
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=ZoneInfo("Asia/Seoul"))
    )


"""
USERS {
    uuid id PK
    text user_name
    datetime created_at
}
"""


class UserBase(SQLModel):
    user_name: str


class UserCreate(UserBase): ...


class UserUpdate(SQLModel):
    user_name: str | None = None


class Users(UserBase, TimeStampMixin, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    analysis_sessions: list["AnalysisSessions"] = Relationship(back_populates="user")
    problems: list["Problems"] = Relationship(back_populates="user")


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


class ProblemBase(SQLModel):
    title: str = Field(max_length=256)
    created_by_user: bool
    user_id: UUID | None = Field(None, foreign_key="users.id")
    university: str | None = Field(None, max_length=32)
    year: int | None = None
    content: str
    model_answer: str | None = None


class ProblemCreate(ProblemBase): ...


class ProblemUpdate(SQLModel):
    title: str | None = None
    content: str | None = None
    model_answer: str | None = None


class Problems(ProblemBase, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    user: Users | None = Relationship(back_populates="problems")
    rubrics: list["Rubrics"] = Relationship(back_populates="problem")
    analysis_sessions: list["AnalysisSessions"] = Relationship(back_populates="problem")


"""
RUBRICS {
    uuid id PK
    uuid problem_id FK
    string criteria
    text description "nullable"
}
"""


class RubricBase(SQLModel):
    problem_id: UUID = Field(foreign_key="problems.id")
    criteria: str = Field(max_length=256)
    description: str | None = None


class RubricCreate(RubricBase): ...


class RubricUpdate(SQLModel):
    criteria: str | None = None
    description: str | None = None


class Rubrics(RubricBase, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    problem: Problems = Relationship(back_populates="rubrics")


"""
ANALYSIS_SESSIONS {
    uuid id PK
    uuid user_id FK
    uuid problem_id FK
    datetime created_at
}
"""


class AnalysisSessionBase(SQLModel):
    user_id: UUID = Field(foreign_key="users.id")
    problem_id: UUID = Field(foreign_key="problems.id")


class AnalysisSessionCreate(AnalysisSessionBase): ...


class AnalysisSessionUpdate(SQLModel): ...


class AnalysisSessions(AnalysisSessionBase, TimeStampMixin, table=True):
    __tablename__ = "analysis_sessions"  # type: ignore
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    user: Users = Relationship(back_populates="analysis_sessions")
    user_answers: list["UserAnswers"] = Relationship(back_populates="analysis_session")
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


class UserAnswerBase(SQLModel):
    session_id: UUID = Field(foreign_key="analysis_sessions.id")
    user_answer: str
    status: Status


class UserAnswerCreate(UserAnswerBase): ...


class UserAnswerUpdate(SQLModel):
    user_answer: str | None = None
    status: Status | None = None


class UserAnswers(UserAnswerBase, table=True):
    __tablename__ = "user_answers"  # type: ignore
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    analysis_session: AnalysisSessions = Relationship(back_populates="user_answers")
    analysis_result: Optional["AnalysisResults"] = Relationship(
        back_populates="user_answer"
    )


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


class AnalysisResultBase(SQLModel):
    answer_id: UUID = Field(foreign_key="user_answers.id")
    grammar_result: GrammarResult = Field(sa_column=Column(PydanticJSON(GrammarResult)))
    criteria_scores: list[CriteriaScore] = Field(
        sa_column=Column(PydanticJSON(list[CriteriaScore]))
    )
    overall_comment: str | None


class AnalysisResultCreate(AnalysisResultBase): ...


class AnalysisResultUpdate(SQLModel):
    grammar_result: GrammarResult | None = None
    criteria_scores: list[CriteriaScore] | None = None
    overall_comment: str | None = None


class AnalysisResults(AnalysisResultBase, TimeStampMixin, table=True):
    __tablename__ = "analysis_results"  # type: ignore
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    user_answer: UserAnswers = Relationship(back_populates="analysis_result")
    chat_session: Optional["ChatSessions"] = Relationship(
        back_populates="analysis_result"
    )


"""
CHAT_SESSIONS {
    uuid id PK
    uuid result_id FK
    datetime created_at
}
"""


class ChatSessionBase(SQLModel):
    result_id: UUID = Field(foreign_key="analysis_results.id")


class ChatSessionCreate(ChatSessionBase): ...


class ChatSessionsUpdate(SQLModel): ...


class ChatSessions(ChatSessionBase, TimeStampMixin, table=True):
    __tablename__ = "chat_sessions"  # type: ignore
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    analysis_result: AnalysisResults = Relationship(back_populates="chat_session")
    chat_messages: list["ChatMessages"] = Relationship(back_populates="chat_session")


"""
CHAT_MESSAGES {
    uuid id PK
    uuid chat_id FK
    string role
    text content
    datetime created_at
}
"""


class ChatMessageBase(SQLModel):
    chat_id: UUID = Field(foreign_key="chat_sessions.id")
    role: str = Field(max_length=10)
    content: str


class ChatMessageCreate(ChatMessageBase): ...


class ChatMessageUpdate(SQLModel):
    role: str | None = None
    content: str | None = None


class ChatMessages(ChatMessageBase, TimeStampMixin, table=True):
    __tablename__ = "chat_messages"  # type: ignore
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    chat_session: ChatSessions = Relationship(back_populates="chat_messages")
