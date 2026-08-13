from .conftest import SAMPLE_GRADING_JSON


def _setup_session(client):
    user = client.post("/api/login", json={"identifier": "채점테스트"}).json()
    problem = client.get("/api/problems").json()[0]
    session = client.post(
        "/api/sessions",
        json={"user_id": user["id"], "problem_id": problem["id"], "problem_source": problem["source"]},
    ).json()
    return session


def test_grade_requires_existing_session(client, fake_claude):
    res = client.post("/api/grade", json={"session_id": 99999, "source": "test"})
    assert res.status_code == 404


def test_grade_requires_existing_answer(client, fake_claude):
    session = _setup_session(client)
    res = client.post("/api/grade", json={"session_id": session["id"], "source": "test"})
    assert res.status_code == 404


def test_grade_computes_score_from_llm_json(client, fake_claude):
    session = _setup_session(client)
    client.post("/api/answers", json={"session_id": session["id"], "text": "테스트 답안", "status": "draft"})

    fake_claude.complete_json.return_value = SAMPLE_GRADING_JSON
    res = client.post("/api/grade", json={"session_id": session["id"], "source": "test"})

    assert res.status_code == 200
    body = res.json()
    # 4/5 + 3/5 = 7/10
    assert body["score"] == 7
    assert body["total_max"] == 10
    assert len(body["scores"]) == 2
    assert body["commentary"] == "테스트용 총평입니다."
    assert body["suggestions"] == ["첫 번째 제안", "두 번째 제안"]
    assert len(body["grammar_errors"]) == 1
    assert body["grammar_errors"][0]["before"] == "테스트 문장"


def test_grade_ignores_malformed_score_items(client, fake_claude):
    session = _setup_session(client)
    client.post("/api/answers", json={"session_id": session["id"], "text": "테스트 답안", "status": "draft"})

    fake_claude.complete_json.return_value = {
        "scores": [
            {"label": "정상 항목", "value": 3, "max_score": 5},
            {"label": "깨진 항목", "value": "숫자아님", "max_score": 5},  # 무시되어야 함
        ],
        "commentary": "",
        "suggestions": [],
        "grammar_errors": [],
    }
    res = client.post("/api/grade", json={"session_id": session["id"], "source": "test"})
    assert res.status_code == 200
    body = res.json()
    assert len(body["scores"]) == 1
    assert body["score"] == 3
    assert body["total_max"] == 5
