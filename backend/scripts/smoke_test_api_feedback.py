"""POST /api/feedback end-to-end 스모크 테스트 (TestClient, 실제 bareun + LLM 호출).

시나리오:
  1) essay_text만 주고 첨삭 (저장 없음)
  2) /api/grading으로 답안을 먼저 만든 뒤, 그 answer_id로 첨삭 요청 -> AnalysisResult.corrections 병합 저장 확인
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app.core.db import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import AnalysisResult, Problem  # noqa: E402

client = TestClient(app)

ESSAY = "나는 오늘 학교에 갔다왔다. 그리고 밥을먹었습니다. 로봇세는 필요하다고 생각한다 왜냐하면 필요하기 때문이다."

# 1) 저장 없이 첨삭만
r1 = client.post("/api/feedback", json={"essay_text": ESSAY})
print(f"=== 1) 저장 없이 첨삭 (status={r1.status_code}) ===")
body1 = r1.json()
print(json.dumps(body1, ensure_ascii=False, indent=2))
assert r1.status_code == 200
assert body1["saved_to_result_id"] is None
assert len(body1["spelling_corrections"]) > 0, "맞춤법 교정이 하나도 없음 (원문에 명백한 오류가 있는데)"

# 2) 답안에 연결해서 저장
db = SessionLocal()
problem = db.query(Problem).filter(Problem.university == "국립국어원", Problem.title.like("%Q1")).one()
problem_id = problem.problem_id
db.close()

r_grade = client.post(
    "/api/grading",
    json={"user_identifier": "feedback-smoke-user", "problem_id": problem_id, "user_answer": ESSAY},
)
assert r_grade.status_code == 200, r_grade.text
answer_id = r_grade.json()["answer_id"]

r2 = client.post("/api/feedback", json={"essay_text": ESSAY, "answer_id": answer_id})
print(f"\n=== 2) answer_id 연결 저장 (status={r2.status_code}) ===")
body2 = r2.json()
print(json.dumps(body2, ensure_ascii=False, indent=2)[:1500])
assert r2.status_code == 200
assert body2["saved_to_result_id"] is not None

# DB에 실제로 병합 저장됐는지, 기존 채점 결과(scores)는 안 지워졌는지 확인
db = SessionLocal()
ar = db.query(AnalysisResult).filter(AnalysisResult.result_id == body2["saved_to_result_id"]).one()
assert ar.corrections is not None and ar.corrections["spelling_corrections"], "corrections가 저장되지 않음"
assert ar.scores is not None, "기존 채점 결과(scores)가 첨삭 저장 과정에서 사라짐"
print("\nDB 확인: corrections 저장됨, 기존 scores 보존됨 -> OK")
db.close()

print("\n\n모든 시나리오 통과.")
