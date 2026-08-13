def test_login_creates_new_user(client):
    res = client.post("/api/login", json={"identifier": "새사용자"})
    assert res.status_code == 200
    body = res.json()
    assert body["identifier"] == "새사용자"
    assert isinstance(body["id"], int)


def test_login_reuses_existing_user(client):
    first = client.post("/api/login", json={"identifier": "기존사용자"}).json()
    second = client.post("/api/login", json={"identifier": "기존사용자"}).json()
    assert first["id"] == second["id"]


def test_login_rejects_empty_identifier(client):
    res = client.post("/api/login", json={"identifier": "   "})
    assert res.status_code == 400
