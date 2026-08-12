from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class Metadata(BaseModel):
    category: Optional[str] = None
    school: Optional[str] = None
    exam_type: Optional[str] = None
    year: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None


class ProblemOut(BaseModel):
    id: int
    title: str
    source: str
    content: str
    rubric: Optional[str] = None
    model_answer: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None

    class Config:
        orm_mode = True


class SessionOut(BaseModel):
    id: int
    user_id: int
    problem_id: Optional[int] = None
    problem_source: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        orm_mode = True


class AnswerCreate(BaseModel):
    session_id: int
    text: str
    status: Optional[str] = "draft"


class AnswerOut(BaseModel):
    id: int
    session_id: int
    text: str
    status: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        orm_mode = True


class SessionCreate(BaseModel):
    user_id: int
    problem_id: int
    problem_source: str


class GradeRequest(BaseModel):
    session_id: int
    source: Optional[str] = "api"


class ScoreItem(BaseModel):
    label: str
    value: int
    total: int


class GradeResultOut(BaseModel):
    session_id: int
    source: str
    score: int
    scores: List[ScoreItem]
    commentary: Optional[str] = None
    grammar_errors: Optional[List[Dict[str, Any]]] = []
    tool_responses: Optional[Dict[str, Any]] = None

    class Config:
        orm_mode = True


class ChatMessageIn(BaseModel):
    session_id: int
    text: str
    metadata: Optional[Dict[str, Any]] = None


class ChatMessageOut(BaseModel):
    id: int
    session_id: int
    role: str
    text: str
    meta: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None

    class Config:
        orm_mode = True


class ChatResponseOut(BaseModel):
    session_id: int
    messages: List[ChatMessageOut]
