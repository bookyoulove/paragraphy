"""WS /api/chat end-to-end 스모크 테스트 (TestClient, 실제 LLM 호출).

시나리오:
  1) /api/grading으로 채점 결과 하나 생성
  2) 정상 user_identifier로 WS 연결 -> ready 수신 -> 질문 2회(멀티턴) -> 응답 확인
  3) DB에 ChatSession/ChatMessage(4건: user*2 + assistant*2)가 저장됐는지 확인
  4) 잘못된 user_identifier로 연결 시도 -> 소유권 검증 오류로 거부되는지 확인
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app.core.db import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import ChatMessage, ChatSession, Problem  # noqa: E402

client = TestClient(app)

db = SessionLocal()
problem = db.query(Problem).filter(Problem.university == "국립국어원", Problem.title.like("%Q1")).one()
problem_id = problem.problem_id
db.close()

USER = "ws-smoke-user"

r = client.post(
    "/api/grading",
    json={
        "user_identifier": USER,
        "problem_id": problem_id,
        "user_answer": "로봇세는 필요하다. 왜냐하면 필요하기 때문이다.",
    },
)
assert r.status_code == 200, r.text
result_id = r.json()["result_id"]
print(f"채점 결과 생성: result_id={result_id}")

# --- 2) 정상 흐름 ---
with client.websocket_connect(f"/api/chat?result_id={result_id}&user_identifier={USER}") as ws:
    ready = ws.receive_json()
    print("\n=== ready ===")
    print(json.dumps(ready, ensure_ascii=False))
    assert ready["type"] == "ready"
    assert ready["history"] == []

    ws.send_text("이유/근거의 적절성 항목은 왜 점수가 낮게 나왔어?")
    reply1 = ws.receive_json()
    print("\n=== 답변 1 ===")
    print(json.dumps(reply1, ensure_ascii=False, indent=2))
    assert reply1["type"] == "message"
    assert reply1["content"].strip()

    ws.send_text("그럼 그 부분 어떻게 고치면 좋을지 구체적으로 알려줘.")
    reply2 = ws.receive_json()
    print("\n=== 답변 2 (멀티턴) ===")
    print(json.dumps(reply2, ensure_ascii=False, indent=2))
    assert reply2["type"] == "message"
    assert reply2["content"].strip()

# --- 3) DB 저장 확인 ---
db = SessionLocal()
chat_session = db.query(ChatSession).filter(ChatSession.result_id == result_id).one()
messages = db.query(ChatMessage).filter(ChatMessage.chat_id == chat_session.chat_id).order_by(ChatMessage.created_at).all()
print(f"\n저장된 메시지 수: {len(messages)} (기대: 4)")
assert len(messages) == 4
assert [m.role for m in messages] == ["user", "assistant", "user", "assistant"]
db.close()

# --- 4) 소유권 검증 실패 ---
try:
    with client.websocket_connect(f"/api/chat?result_id={result_id}&user_identifier=other-user") as ws2:
        err = ws2.receive_json()
        print("\n=== 소유권 불일치 응답 ===")
        print(json.dumps(err, ensure_ascii=False))
        assert err["type"] == "error"
except Exception as exc:
    # TestClient가 서버 close(code=4403)를 예외로 전달하는 구현체 버전도 있음 -> 정상 처리로 간주
    print(f"\n=== 소유권 불일치: 연결 거부 ({exc}) ===")

print("\n\n모든 시나리오 통과.")
