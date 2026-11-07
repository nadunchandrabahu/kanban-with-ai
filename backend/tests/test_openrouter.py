import json

import pytest
from fastapi import HTTPException

from app.models import BoardData, ChatMessage
import app.openrouter as openrouter


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class FakeClient:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        _ = exc_type, exc, tb

    def post(self, url, headers, json):
        self.calls.append((url, headers, json))
        return FakeResponse(self.payload)


def test_headers_requires_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(HTTPException):
        openrouter._headers()


def test_parse_response_content():
    content = json.dumps({"assistant_reply": "ok", "updated_board": None})
    parsed = openrouter._parse_response_content(content)
    assert parsed.assistant_reply == "ok"
    assert parsed.updated_board is None


def test_ask_ai(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    fake_client = FakeClient(
        {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {"assistant_reply": "done", "updated_board": None}
                        )
                    }
                }
            ]
        }
    )
    monkeypatch.setattr(openrouter.httpx, "Client", lambda timeout: fake_client)
    board = BoardData(columns=[], cards={})
    result = openrouter.ask_ai(board, [ChatMessage(role="user", content="hello")], "help")
    assert result.assistant_reply == "done"
    assert fake_client.calls[0][2]["model"] == openrouter.MODEL_NAME


def test_ping_ai(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    fake_client = FakeClient({"choices": [{"message": {"content": "4"}}]})
    monkeypatch.setattr(openrouter.httpx, "Client", lambda timeout: fake_client)
    assert openrouter.ping_ai() == "4"
