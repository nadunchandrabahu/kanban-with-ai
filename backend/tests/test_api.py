def auth_headers() -> dict[str, str]:
    return {"x-username": "user", "x-password": "password"}


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_verify_auth(client):
    ok = client.post("/api/auth/verify", json={"username": "user", "password": "password"})
    bad = client.post("/api/auth/verify", json={"username": "user", "password": "nope"})
    assert ok.status_code == 200
    assert ok.json() == {"ok": True}
    assert bad.json() == {"ok": False}


def test_board_requires_auth(client):
    response = client.get("/api/board")
    assert response.status_code == 401


def test_board_update_round_trip(client):
    board = client.get("/api/board", headers=auth_headers()).json()
    board["columns"][0]["title"] = "Renamed"
    update = client.put("/api/board", headers=auth_headers(), json=board)
    assert update.status_code == 200
    latest = client.get("/api/board", headers=auth_headers()).json()
    assert latest["columns"][0]["title"] == "Renamed"


def test_chat_history_and_chat(mocked_client_with_ai):
    client = mocked_client_with_ai
    response = client.post("/api/chat", headers=auth_headers(), json={"message": "hello"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["message"] == "AI reply"
    assert payload["board_updated"] is False
    history = client.get("/api/chat/history", headers=auth_headers())
    assert history.status_code == 200
    assert len(history.json()) == 2


def test_chat_can_update_board(mocked_client_with_ai_board_update):
    client = mocked_client_with_ai_board_update
    response = client.post("/api/chat", headers=auth_headers(), json={"message": "add a column"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["board_updated"] is True
    latest = client.get("/api/board", headers=auth_headers()).json()
    assert latest["columns"][-1]["title"] == "New Column"


def test_ai_ping(mocked_client_with_ping):
    client = mocked_client_with_ping
    response = client.get("/api/ai/ping", headers=auth_headers())
    assert response.status_code == 200
    assert "4" in response.json()["answer"]
