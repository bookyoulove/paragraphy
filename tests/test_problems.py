def test_list_problems_returns_real_seed_data(client):
    res = client.get("/api/problems")
    assert res.status_code == 200
    problems = res.json()
    # seed_data.py는 한양대 2, 경희대 2, 국립국어원 1개를 실제 문서에서 파싱해 적재한다.
    assert len(problems) == 5
    sources = {p["source"] for p in problems}
    assert sources == {"한양대", "경희대", "국립국어원"}
    for p in problems:
        assert p["content"].strip() != ""
        assert p["title"].strip() != ""


def test_get_problem_404_for_missing(client):
    res = client.get("/api/problems/99999")
    assert res.status_code == 404


def test_get_problem_returns_matching_id(client):
    listed = client.get("/api/problems").json()
    target = listed[0]
    res = client.get(f"/api/problems/{target['id']}")
    assert res.status_code == 200
    assert res.json()["id"] == target["id"]


def test_create_user_submitted_problem(client):
    payload = {
        "title": "테스트 문제",
        "content": "테스트 지문과 문항입니다.",
        "rubric": "1. 항목 A (50점)\n2. 항목 B (50점)",
    }
    res = client.post("/api/problems", json=payload)
    assert res.status_code == 200
    body = res.json()
    assert body["source"] == "사용자입력"
    assert body["meta"]["category"] == "사용자입력"
    assert body["rubric"] == payload["rubric"]

    # 목록에도 반영되어야 한다
    listed = client.get("/api/problems").json()
    assert any(p["id"] == body["id"] for p in listed)
