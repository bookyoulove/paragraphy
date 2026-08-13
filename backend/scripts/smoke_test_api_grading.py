"""POST /api/grading end-to-end 스모크 테스트 (TestClient, 실제 LLM 호출 + 실제 DB 사용).

시나리오:
  1) 문제은행 문제로 1차 채점
  2) 같은 session_id로 2차 채점 (답안을 개선) -> previous_comparison 확인
  3) 사용자 직접 입력 문제 (rubric_items 포함) 채점
  4) rubric_items 없이 직접입력 문제 요청 -> 422 검증 오류 확인
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app.core.db import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Problem  # noqa: E402

db = SessionLocal()
problem = db.query(Problem).filter(Problem.university == "국립국어원", Problem.title.like("%Q1")).one()
problem_id = problem.problem_id
db.close()

client = TestClient(app)


def pp(label: str, resp) -> dict:
    print(f"\n=== {label} (status={resp.status_code}) ===")
    body = resp.json()
    print(json.dumps(body, ensure_ascii=False, indent=2)[:2000])
    return body


# 1) 문제은행 문제로 1차 채점 (일부러 짧고 부실한 답안)
r1 = client.post(
    "/api/grading",
    json={
        "user_identifier": "smoke-test-user",
        "problem_id": problem_id,
        "user_answer": "로봇세는 필요하다. 왜냐하면 필요하기 때문이다.",
    },
)
body1 = pp("1차 채점 (문제은행)", r1)
assert r1.status_code == 200, "1차 채점 실패"
session_id = body1["session_id"]

# 2) 같은 세션에서 2차 채점 (답안 개선)
r2 = client.post(
    "/api/grading",
    json={
        "user_identifier": "smoke-test-user",
        "problem_id": problem_id,
        "session_id": session_id,
        "user_answer": (
            "로봇세는 도입해야 한다. 로봇의 발달로 일자리를 잃는 노동자가 늘고 있으며, "
            "이들의 재교육과 사회 안전망 구축에는 막대한 재원이 필요하기 때문이다. "
            "다만 세율을 지나치게 높이면 기술 혁신이 위축될 수 있으므로, 초기에는 낮은 세율로 "
            "시작해 점진적으로 조정하는 방안이 현실적이다."
        ),
    },
)
body2 = pp("2차 채점 (같은 세션, 개선된 답안)", r2)
assert r2.status_code == 200, "2차 채점 실패"
assert body2["round"] == 2, f"round가 2가 아님: {body2['round']}"
assert body2["previous_comparison"] is not None, "previous_comparison이 없음"

# 3) 사용자 직접 입력 문제
r3 = client.post(
    "/api/grading",
    json={
        "user_identifier": "smoke-test-user",
        "problem_content": "행복이란 무엇인지 자신의 경험을 바탕으로 서술하시오.",
        "rubric_items": [
            {"criteria": "경험의 구체성", "description": "자신의 실제 경험을 구체적으로 서술하는가"},
            {"criteria": "논지의 일관성", "description": "행복에 대한 자신의 관점이 글 전체에서 일관되는가"},
        ],
        "user_answer": "나는 작년에 가족과 여행을 갔을 때 행복을 느꼈다. 함께 웃고 이야기 나누는 시간이 소중했다.",
    },
)
body3 = pp("3차 (사용자 직접 입력 문제)", r3)
assert r3.status_code == 200, "직접입력 문제 채점 실패"

# 4) rubric_items 없이 직접입력 문제 요청 -> 검증 오류
r4 = client.post(
    "/api/grading",
    json={
        "user_identifier": "smoke-test-user",
        "problem_content": "행복이란 무엇인지 서술하시오.",
        "user_answer": "행복은 사람마다 다르다.",
    },
)
print(f"\n=== 4) rubric_items 누락 -> 검증 오류 (status={r4.status_code}) ===")
print(json.dumps(r4.json(), ensure_ascii=False, indent=2)[:500])
assert r4.status_code == 422, f"검증 오류가 발생해야 하는데 status={r4.status_code}"

print("\n\n모든 시나리오 통과.")
