def _setup_session(client):
    user = client.post("/api/login", json={"identifier": "비교테스트"}).json()
    problem = client.get("/api/problems").json()[0]
    return client.post(
        "/api/sessions",
        json={"user_id": user["id"], "problem_id": problem["id"], "problem_source": problem["source"]},
    ).json()


def test_results_requires_existing_session(client):
    res = client.get("/api/sessions/99999/results")
    assert res.status_code == 404


def test_results_empty_before_any_grading(client):
    session = _setup_session(client)
    res = client.get(f"/api/sessions/{session['id']}/results")
    assert res.status_code == 200
    assert res.json() == []


def test_results_track_multiple_grading_attempts(client, fake_claude):
    session = _setup_session(client)

    client.post("/api/answers", json={"session_id": session["id"], "text": "초안 1", "status": "draft"})
    fake_claude.complete_json.return_value = {
        "scores": [{"label": "주장", "value": 2, "max_score": 5}],
        "commentary": "1회차",
        "suggestions": [],
        "grammar_errors": [{"type": "논리 비약", "before": "a", "after": "b", "note": "n"}],
    }
    client.post("/api/grade", json={"session_id": session["id"], "source": "test"})

    client.post("/api/answers", json={"session_id": session["id"], "text": "개선된 답안", "status": "draft"})
    fake_claude.complete_json.return_value = {
        "scores": [{"label": "주장", "value": 4, "max_score": 5}],
        "commentary": "2회차",
        "suggestions": [],
        "grammar_errors": [],
    }
    client.post("/api/grade", json={"session_id": session["id"], "source": "test"})

    res = client.get(f"/api/sessions/{session['id']}/results")
    assert res.status_code == 200
    results = res.json()
    assert len(results) == 2
    assert [r["attempt"] for r in results] == [1, 2]
    # 각 회차 점수 + 시스템이 자동 추가하는 "문법과 어휘" 5/5 (Bareun 오류 0건 → 만점)
    assert results[0]["score"] == 7
    assert results[0]["grammar_error_count"] == 1
    assert results[1]["score"] == 9
    assert results[1]["grammar_error_count"] == 0
    # 회차가 오래된 순으로 정렬되어 있어야 한다 (비교표는 최신 회차가 마지막 열)
    assert results[0]["created_at"] <= results[1]["created_at"]
    # 각 회차 채점 시점의 답안 원문이 스냅샷으로 남아있어야 한다 (비교표에서 회차 클릭 시 복원용)
    assert results[0]["answer_text"] == "초안 1"
    assert results[1]["answer_text"] == "개선된 답안"
