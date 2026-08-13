from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict


class ProblemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    source: str
    content: str
    rubric: Optional[str] = None
    model_answer: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    problem_id: Optional[int] = None
    problem_source: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AnswerCreate(BaseModel):
    session_id: int
    text: str
    status: Optional[str] = "draft"


class AnswerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    text: str
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SessionCreate(BaseModel):
    user_id: int
    problem_id: int
    problem_source: str


class LoginRequest(BaseModel):
    identifier: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    identifier: str


class RubricGenerateRequest(BaseModel):
    title: Optional[str] = None
    content: str
    hint: Optional[str] = None


class RubricGenerateOut(BaseModel):
    rubric: str


class ProblemCreate(BaseModel):
    title: str
    content: str
    rubric: Optional[str] = None
    model_answer: Optional[str] = None
    created_by: Optional[int] = None


class GradeRequest(BaseModel):
    session_id: int
    source: Optional[str] = "api"


class ScoreItem(BaseModel):
    label: str
    value: int
    max_score: int


class GradeResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: int
    source: str
    score: int
    total_max: int
    scores: List[ScoreItem]
    commentary: Optional[str] = None
    suggestions: Optional[List[str]] = []
    grammar_errors: Optional[List[Dict[str, Any]]] = []


class ResultSummaryOut(BaseModel):
    id: int
    attempt: int
    created_at: Optional[datetime] = None
    score: int
    total_max: int
    scores: List[ScoreItem]
    grammar_error_count: int
    commentary: Optional[str] = None
    suggestions: Optional[List[str]] = []
    grammar_errors: Optional[List[Dict[str, Any]]] = []


class SessionHistoryOut(BaseModel):
    id: int
    problem_id: Optional[int] = None
    problem_title: str
    problem_source: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    attempt_count: int
    latest_score: Optional[int] = None
    latest_total_max: Optional[int] = None


class ChatMessageIn(BaseModel):
    session_id: int
    text: str
    meta: Optional[Dict[str, Any]] = None


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    role: str
    text: str
    meta: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None


class ChatResponseOut(BaseModel):
    session_id: int
    messages: List[ChatMessageOut]
