def _login(client, identifier="유진"):
    return client.post("/api/login", json={"identifier": identifier}).json()


def _first_problem(client):
    return client.get("/api/problems").json()[0]


def test_create_session_requires_existing_user(client):
    problem = _first_problem(client)
    res = client.post(
        "/api/sessions",
        json={"user_id": 99999, "problem_id": problem["id"], "problem_source": problem["source"]},
    )
    assert res.status_code == 404


def test_create_session_success(client):
    user = _login(client)
    problem = _first_problem(client)
    res = client.post(
        "/api/sessions",
        json={"user_id": user["id"], "problem_id": problem["id"], "problem_source": problem["source"]},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["user_id"] == user["id"]
    assert body["problem_id"] == problem["id"]


def test_submit_answer_requires_existing_session(client):
    res = client.post("/api/answers", json={"session_id": 99999, "text": "답안", "status": "draft"})
    assert res.status_code == 404


def test_submit_answer_upserts_draft(client, db_session):
    from backend.models import UserAnswer

    user = _login(client)
    problem = _first_problem(client)
    session = client.post(
        "/api/sessions",
        json={"user_id": user["id"], "problem_id": problem["id"], "problem_source": problem["source"]},
    ).json()

    first = client.post(
        "/api/answers", json={"session_id": session["id"], "text": "초안 1", "status": "draft"}
    ).json()
    second = client.post(
        "/api/answers", json={"session_id": session["id"], "text": "초안 2 (수정됨)", "status": "draft"}
    ).json()

    # 같은 세션의 draft 답안은 새 row가 아니라 upsert되어야 한다 (설계: 세션 단위 upsert)
    assert first["id"] == second["id"]
    assert second["text"] == "초안 2 (수정됨)"

    rows = db_session.query(UserAnswer).filter(UserAnswer.session_id == session["id"]).all()
    assert len(rows) == 1
