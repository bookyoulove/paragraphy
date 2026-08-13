"""SQLAlchemy engine / session 설정.

초기 개발 단계는 SQLite. 이후 PostgreSQL(JSONB)로 전환 시
`settings.database_url` 및 Base.metadata.create_all 호출부만 바꾸면 되도록
모델은 SQLAlchemy 2.0 표준 타입으로 작성한다 (JSON 컬럼은 SQLite/Postgres 공통 호환).
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI Depends 주입용 DB 세션 (컴포넌트 설계서 4.2 저장소 접근 방식 준수)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()