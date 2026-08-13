"""GET /api/sessions, GET /api/sessions/{id} 스모크 테스트 (실제 LLM로 2회차 채점 생성)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app.core.db import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Problem  # noqa: E402

client = TestClient(app)
USER = "history-smoke-user"

db = SessionLocal()
problem = db.query(Problem).filter(Problem.university == "국립국어원", Problem.title.like("%Q1")).one()
problem_id = problem.problem_id
db.close()

r1 = client.post(
    "/api/grading",
    json={"user_identifier": USER, "problem_id": problem_id, "user_answer": "로봇세는 필요하다. 왜냐하면 필요하기 때문이다."},
)
assert r1.status_code == 200, r1.text
session_id = r1.json()["session_id"]

r2 = client.post(
    "/api/grading",
    json={
        "user_identifier": USER,
        "problem_id": problem_id,
        "session_id": session_id,
        "user_answer": "로봇세는 도입해야 한다. 일자리를 잃는 노동자를 지원할 재원이 필요하기 때문이다.",
    },
)
assert r2.status_code == 200, r2.text

r_list = client.get(f"/api/sessions?user_identifier={USER}")
body_list = r_list.json()
print("=== GET /api/sessions ===")
print(json.dumps(body_list, ensure_ascii=False, indent=2))
assert r_list.status_code == 200
assert len(body_list) == 1
assert body_list[0]["round_count"] == 2

r_detail = client.get(f"/api/sessions/{session_id}")
body_detail = r_detail.json()
print("\n=== GET /api/sessions/{id} ===")
print(json.dumps(body_detail, ensure_ascii=False, indent=2)[:2000])
assert r_detail.status_code == 200
assert len(body_detail["rounds"]) == 2
assert body_detail["rounds"][0]["round"] == 1
assert body_detail["rounds"][1]["round"] == 2

print("\n\n모든 시나리오 통과.")
