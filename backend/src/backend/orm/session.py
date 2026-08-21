import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, create_engine

from backend.orm.models import *

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL is None:
    db_path = Path(__file__).resolve().parents[4] / "db" / "database.db"
    DATABASE_URL = f"sqlite:///{db_path}"

connect_args = {"check_same_thread": False}
db_engine = create_engine(DATABASE_URL, connect_args=connect_args)


def create_db_and_table():
    SQLModel.metadata.create_all(db_engine)
    _migrate_sqlite_problem_columns()
    _ensure_analysis_session_index()


def _migrate_sqlite_problem_columns() -> None:
    """Apply small, additive SQLite schema changes without deleting existing data."""
    if db_engine.dialect.name != "sqlite":
        return

    inspector = inspect(db_engine)
    if "problems" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("problems")}
    if "source_report_id" not in columns:
        with db_engine.begin() as connection:
            connection.exec_driver_sql(
                "ALTER TABLE problems ADD COLUMN source_report_id CHAR(32)"
            )


def _ensure_analysis_session_index() -> None:
    # create_all() does not alter tables that already exist. Keep the
    # application invariant in place for an existing development database too.
    with db_engine.begin() as connection:
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS "
                "uq_analysis_sessions_user_problem "
                "ON analysis_sessions (user_id, problem_id)"
            )
        )


def get_session():
    with Session(db_engine) as session:
        yield session
