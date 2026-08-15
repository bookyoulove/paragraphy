import os
from pathlib import Path

from dotenv import load_dotenv
from sqlmodel import Session, SQLModel, create_engine

from backend.orm.models import *

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL is None:
    db_path = Path(__file__).resolve().parents[4] / "db" / "database.db"
    DATABASE_URL = f"sqlite:///{db_path}"

# SQLite는 스레드 검사 해제가 필요하지만, PostgreSQL(Neon)에 같은 옵션을
# 전달하면 연결 오류가 난다. DATABASE_URL에 따라 적절한 엔진 옵션만 사용한다.
engine_options = {"connect_args": {"check_same_thread": False}} if DATABASE_URL.startswith("sqlite") else {}
db_engine = create_engine(DATABASE_URL, **engine_options)


def create_db_and_table():
    SQLModel.metadata.create_all(db_engine)


def get_session():
    with Session(db_engine) as session:
        yield session
