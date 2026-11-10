import json

import pytest

import app.openrouter as openrouter


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


def test_chat_returns_sanitized_provider_error(mocked_client_with_ai_provider_error):
    client = mocked_client_with_ai_provider_error
    response = client.post("/api/chat", headers=auth_headers(), json={"message": "hello"})
    assert response.status_code == 502
    assert "temporarily unavailable" in response.json()["detail"].lower()
    assert "apikey" not in response.json()["detail"].lower()
    assert "key=" not in response.json()["detail"].lower()


def test_board_rejects_malformed_payload(client):
    empty_title = {"columns": [{"id": "c1", "title": "", "cardIds": []}], "cards": {}}
    wrong_type = {"columns": "nope", "cards": {}}
    for payload in (empty_title, wrong_type):
        response = client.put("/api/board", headers=auth_headers(), json=payload)
        assert response.status_code == 422


@pytest.mark.parametrize(
    ("board", "error"),
    [
        (
            {"columns": [{"id": "c1", "title": "A", "cardIds": ["missing"]}], "cards": {}},
            "every cardid must exist",
        ),
        (
            {
                "columns": [{"id": "c1", "title": "A", "cardIds": []}],
                "cards": {"x": {"id": "x", "title": "Orphan"}},
            },
            "every card must be in exactly one column",
        ),
        (
            {
                "columns": [
                    {"id": "c1", "title": "A", "cardIds": ["x"]},
                    {"id": "c2", "title": "B", "cardIds": ["x"]},
                ],
                "cards": {"x": {"id": "x", "title": "Twice"}},
            },
            "only one column",
        ),
        (
            {
                "columns": [{"id": "c1", "title": "A", "cardIds": ["x"]}],
                "cards": {"x": {"id": "y", "title": "Wrong key"}},
            },
            "does not match card id",
        ),
        (
            {
                "columns": [
                    {"id": "c1", "title": "A", "cardIds": []},
                    {"id": "c1", "title": "B", "cardIds": []},
                ],
                "cards": {},
            },
            "column ids must be unique",
        ),
    ],
)
def test_board_rejects_inconsistent_board(client, board, error):
    response = client.put("/api/board", headers=auth_headers(), json=board)
    assert response.status_code == 422
    assert error in response.text.lower()
    assert client.get("/api/board", headers=auth_headers()).json()["columns"][0]["id"] == "col-backlog"


def test_chat_requires_auth(client):
    response = client.post("/api/chat", json={"message": "hello"})
    assert response.status_code == 401


def gemini_reply(text: str) -> dict:
    return {"candidates": [{"content": {"parts": [{"text": text}]}}]}


def test_chat_rejects_inconsistent_ai_board(client, monkeypatch):
    bad_board = {"columns": [{"id": "c1", "title": "A", "cardIds": ["ghost"]}], "cards": {}}
    reply = json.dumps({"assistant_reply": "Done", "updated_board": bad_board})
    monkeypatch.setattr(openrouter, "_post_with_retry", lambda body, timeout_seconds: gemini_reply(reply))
    before = client.get("/api/board", headers=auth_headers()).json()
    response = client.post("/api/chat", headers=auth_headers(), json={"message": "break it"})
    assert response.status_code == 502
    assert client.get("/api/board", headers=auth_headers()).json() == before
    assert client.get("/api/chat/history", headers=auth_headers()).json() == []


@pytest.mark.parametrize(
    ("data", "detail"),
    [
        ({"promptFeedback": {"blockReason": "SAFETY"}}, "no content"),
        ({"candidates": [{"finishReason": "SAFETY"}]}, "no content"),
        (gemini_reply("not json"), "ai request failed"),
        (gemini_reply("[1, 2]"), "ai request failed"),
    ],
)
def test_chat_bad_ai_response_returns_502(client, monkeypatch, data, detail):
    monkeypatch.setattr(openrouter, "_post_with_retry", lambda body, timeout_seconds: data)
    response = client.post("/api/chat", headers=auth_headers(), json={"message": "hi"})
    assert response.status_code == 502
    assert detail in response.json()["detail"].lower()


def test_ai_ping_no_content_returns_502(client, monkeypatch):
    monkeypatch.setattr(openrouter, "_post_with_retry", lambda body, timeout_seconds: {})
    response = client.get("/api/ai/ping", headers=auth_headers())
    assert response.status_code == 502


def test_chat_missing_api_key(client, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    response = client.post("/api/chat", headers=auth_headers(), json={"message": "hi"})
    assert response.status_code == 500
    assert response.json()["detail"] == "GEMINI_API_KEY is missing."


def test_cors_only_allows_dev_origin(client):
    def preflight(origin: str):
        return client.options(
            "/api/board",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "PUT",
                "Access-Control-Request-Headers": "x-username,x-password,content-type",
            },
        )

    allowed = preflight("http://localhost:3000")
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:3000"
    blocked = preflight("https://evil.example")
    assert "access-control-allow-origin" not in blocked.headers
    simple = client.get("/api/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in simple.headers
