from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    identifier = Column(String(128), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.datetime("now"))
    updated_at = Column(DateTime(timezone=True), onupdate=func.datetime("now"))

    sessions = relationship("AnalysisSession", back_populates="user")


class Problem(Base):
    __tablename__ = "problems"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(256), nullable=False)
    source = Column(String(128), nullable=False)
    content = Column(Text, nullable=False)
    rubric = Column(Text, nullable=True)
    model_answer = Column(Text, nullable=True)
    meta = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.datetime("now"))

    sessions = relationship("AnalysisSession", back_populates="problem")


class AnalysisSession(Base):
    __tablename__ = "analysis_sessions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    problem_id = Column(Integer, ForeignKey("problems.id"), nullable=True)
    problem_source = Column(String(64), nullable=False, default="unknown")
    created_at = Column(DateTime(timezone=True), server_default=func.datetime("now"))
    updated_at = Column(DateTime(timezone=True), onupdate=func.datetime("now"))

    user = relationship("User", back_populates="sessions")
    problem = relationship("Problem", back_populates="sessions")
    answers = relationship("UserAnswer", back_populates="session")
    results = relationship("AnalysisResult", back_populates="session")
    chats = relationship("ChatMessage", back_populates="session")


class UserAnswer(Base):
    __tablename__ = "user_answers"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("analysis_sessions.id"), nullable=False)
    text = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="draft")
    created_at = Column(DateTime(timezone=True), server_default=func.datetime("now"))
    updated_at = Column(DateTime(timezone=True), onupdate=func.datetime("now"))

    session = relationship("AnalysisSession", back_populates="answers")


class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("analysis_sessions.id"), nullable=False)
    source = Column(String(64), nullable=False, default="claude")
    scores = Column(JSON, nullable=True)
    grammar_errors = Column(JSON, nullable=True)
    suggestions = Column(JSON, nullable=True)
    commentary = Column(Text, nullable=True)
    tool_responses = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.datetime("now"))

    session = relationship("AnalysisSession", back_populates="results")


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("analysis_sessions.id"), nullable=False)
    role = Column(String(32), nullable=False)
    text = Column(Text, nullable=False)
    meta = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.datetime("now"))

    session = relationship("AnalysisSession", back_populates="chats")
