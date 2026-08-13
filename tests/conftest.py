"""pytest 공용 픽스처.

핵심 원칙:
- 실제 개발용 DB(paragraphy.db)를 절대 건드리지 않는다 (테스트 전용 임시 sqlite 파일 사용).
- 실제 LLM(claude-fable-5)이나 Bareun API에 네트워크 호출을 하지 않는다 (전부 모킹).
  실 API를 검증하는 것은 이 테스트 스위트의 목적이 아니다 — 비용/속도/비결정성 때문에
  라우트·서비스 로직만 빠르고 결정론적으로 검증한다.
"""

import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

# backend.config가 import되기 전에 반드시 먼저 세팅해야 한다 (load_dotenv는 기존 env를 덮어쓰지 않음).
_TEST_DB_PATH = Path(tempfile.gettempdir()) / "paragraphy_test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_PATH}"
os.environ.setdefault("CLAUDE_FABLE5_API_URL", "https://example.invalid")
os.environ.setdefault("CLAUDE_FABLE5_API_KEY", "test-key")
os.environ.setdefault("BAREUN_API_KEY", "test-key")
os.environ.setdefault("ENVIRONMENT", "test")

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest
from starlette.testclient import TestClient

from backend.database import Base, engine, SessionLocal
from backend.routes import app


@pytest.fixture(autouse=True)
def _fresh_schema():
    """매 테스트마다 스키마를 비운 상태로 시작한다."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def _no_real_bareun(monkeypatch):
    """서비스 계층에서 실제 Bareun 네트워크 호출을 막는다.

    bareun_client.check_spelling 자체의 로직(오탐 필터링 등)은 test_bareun.py에서
    별도로 직접 테스트한다.
    """
    monkeypatch.setattr("backend.service.check_spelling", lambda text: [])


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def fake_claude(monkeypatch):
    """backend.service.ClaudeClient를 대체하는 가짜 클라이언트.

    사용 예:
        fake_claude.complete_json.return_value = {...}  # Grading/Rubric Agent용
        fake_claude.chat.return_value = SimpleNamespace(content="...", tool_calls=None)  # Tutor Chat용
    """
    fake_client = MagicMock()
    fake_client.complete_json = AsyncMock()
    fake_client.chat = AsyncMock(return_value=SimpleNamespace(content="", tool_calls=None))
    monkeypatch.setattr("backend.service.ClaudeClient", lambda: fake_client)
    return fake_client


SAMPLE_GRADING_JSON = {
    "scores": [
        {"label": "문제 상황 제시", "value": 4, "max_score": 5},
        {"label": "주장", "value": 3, "max_score": 5},
    ],
    "commentary": "테스트용 총평입니다.",
    "suggestions": ["첫 번째 제안", "두 번째 제안"],
    "grammar_errors": [
        {"type": "논리 비약", "before": "테스트 문장", "after": "수정된 문장", "note": "테스트 근거"}
    ],
}
