from datetime import datetime
from enum import StrEnum
from typing import Any, Optional, override
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from pydantic import TypeAdapter
from shared.schema.analysis import AnalysisResult as AnalysisResultBase
from shared.schema.analysis import CriteriaScore
from shared.schema.grammar import GrammarResult
from shared.schema.problem import ProblemContent
from shared.schema.rubric import Rubric as RubricBase
from shared.schema.skill_report import SkillAssessment
from shared.schema.tutor import ChatMessage as ChatMessageBase
from sqlmodel import (
    JSON,
    Column,
    Field,
    Relationship,
    SQLModel,
    TypeDecorator,
)


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


class Users(UserBase, TimeStampMixin, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    analysis_sessions: list["AnalysisSessions"] = Relationship(back_populates="user")
    problems: list["Problems"] = Relationship(back_populates="user")
    skill_reports: list["UserSkillReports"] = Relationship(back_populates="user")
    coach_messages: list["CoachMessages"] = Relationship(back_populates="user")


"""
USER_SKILL_REPORTS {
    uuid id PK
    uuid user_id FK
    string period_type
    datetime period_start
    datetime period_end
    int review_count
    json skill_scores
    text overall_skill_comment
    text next_learning_goal
    json recommended_actions
    datetime created_at
}
"""


class UserSkillReportBase(SQLModel):
    period_type: str = Field(default="weekly", max_length=16)
    period_start: datetime
    period_end: datetime
    review_count: int = Field(ge=1)
    overall_skill_comment: str
    next_learning_goal: str
    recommended_actions: list[str] = Field(sa_column=Column(PydanticJSON(list[str])))


class UserSkillReports(UserSkillReportBase, TimeStampMixin, table=True):
    __tablename__ = "user_skill_reports"  # type: ignore
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id")
    skill_scores: list[SkillAssessment] = Field(
        sa_column=Column(PydanticJSON(list[SkillAssessment]))
    )

    user: Users = Relationship(back_populates="skill_reports")
    coach_messages: list["CoachMessages"] = Relationship(back_populates="skill_report")


"""
COACH_MESSAGES {
    uuid id PK
    uuid user_id FK
    uuid skill_report_id FK
    string recipient_email
    string message_type
    string title
    text content
    string status
    datetime scheduled_at
    datetime sent_at
    datetime created_at
}
"""


class CoachMessageStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class CoachMessageBase(SQLModel):
    recipient_email: str = Field(max_length=320)
    message_type: str = Field(default="weekly_report", max_length=32)
    title: str = Field(max_length=200)
    content: str
    status: CoachMessageStatus = Field(default=CoachMessageStatus.PENDING)
    scheduled_at: datetime | None = None
    sent_at: datetime | None = None


class CoachMessages(CoachMessageBase, TimeStampMixin, table=True):
    __tablename__ = "coach_messages"  # type: ignore
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id")
    skill_report_id: UUID = Field(foreign_key="user_skill_reports.id")

    user: Users = Relationship(back_populates="coach_messages")
    skill_report: UserSkillReports = Relationship(back_populates="coach_messages")


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


class ProblemBase(ProblemContent):
    created_by_user: bool
    university: str | None = Field(None, max_length=32)
    year: int | None = None


class Problems(ProblemBase, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID | None = Field(None, foreign_key="users.id")
    source_report_id: UUID | None = Field(None, foreign_key="user_skill_reports.id")

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


class Rubrics(RubricBase, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    problem_id: UUID = Field(foreign_key="problems.id")

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
    pass


class AnalysisSessions(AnalysisSessionBase, TimeStampMixin, table=True):
    __tablename__ = "analysis_sessions"  # type: ignore
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id")
    problem_id: UUID = Field(foreign_key="problems.id")

    user: Users = Relationship(back_populates="analysis_sessions")
    user_answers: list["UserAnswers"] = Relationship(
        back_populates="analysis_session",
        sa_relationship_kwargs={"order_by": "UserAnswers.created_at"},
    )
    problem: Problems = Relationship(back_populates="analysis_sessions")


"""
USER_ANSWERS {
    uuid id PK
    uuid session_id FK
    text user_answer
    string status
    string name
    datetime created_at
}
"""


class Status(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"


class UserAnswerBase(SQLModel):
    user_answer: str
    status: Status
    name: str = Field(max_length=50)


class UserAnswers(UserAnswerBase, TimeStampMixin, table=True):
    __tablename__ = "user_answers"  # type: ignore
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    session_id: UUID = Field(foreign_key="analysis_sessions.id")

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


class AnalysisResults(AnalysisResultBase, TimeStampMixin, table=True):
    __tablename__ = "analysis_results"  # type: ignore
    grammar_result: GrammarResult = Field(sa_column=Column(PydanticJSON(GrammarResult)))
    criteria_scores: list[CriteriaScore] = Field(
        sa_column=Column(PydanticJSON(list[CriteriaScore]))
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    answer_id: UUID = Field(foreign_key="user_answers.id")

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
    pass


class ChatSessions(ChatSessionBase, TimeStampMixin, table=True):
    __tablename__ = "chat_sessions"  # type: ignore
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    result_id: UUID = Field(foreign_key="analysis_results.id")

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


class ChatMessages(ChatMessageBase, TimeStampMixin, table=True):
    __tablename__ = "chat_messages"  # type: ignore
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    chat_id: UUID = Field(foreign_key="chat_sessions.id")

    chat_session: ChatSessions = Relationship(back_populates="chat_messages")
