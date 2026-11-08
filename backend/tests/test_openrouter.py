import json

import pytest
from fastapi import HTTPException
import httpx

from app.models import BoardData, ChatMessage
import app.openrouter as openrouter


class FakeResponse:
    def __init__(self, payload, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code
        self.request = httpx.Request("POST", "https://example.test")

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"status {self.status_code}",
                request=self.request,
                response=httpx.Response(self.status_code, request=self.request),
            )

    def json(self):
        return self._payload


class FakeClient:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []
        self._index = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        _ = exc_type, exc, tb

    def post(self, url, headers, json):
        self.calls.append((url, headers, json))
        if isinstance(self.payload, list):
            item = self.payload[min(self._index, len(self.payload) - 1)]
            self._index += 1
            if isinstance(item, tuple):
                body, status_code = item
                return FakeResponse(body, status_code=status_code)
            return FakeResponse(item)
        if isinstance(self.payload, tuple):
            body, status_code = self.payload
            return FakeResponse(body, status_code=status_code)
        return FakeResponse(self.payload)


def test_headers_requires_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(HTTPException):
        openrouter._api_key()


def test_parse_response_content():
    content = json.dumps({"assistant_reply": "ok", "updated_board": None})
    parsed = openrouter._parse_response_content(content)
    assert parsed.assistant_reply == "ok"
    assert parsed.updated_board is None


def test_ask_ai(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    fake_client = FakeClient(
        {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": json.dumps(
                            {"assistant_reply": "done", "updated_board": None}
                        )
                            }
                        ]
                    }
                }
            ]
        }
    )
    monkeypatch.setattr(openrouter.httpx, "Client", lambda timeout: fake_client)
    board = BoardData(columns=[], cards={})
    result = openrouter.ask_ai(board, [ChatMessage(role="user", content="hello")], "help")
    assert result.assistant_reply == "done"
    assert "generationConfig" in fake_client.calls[0][2]


def test_ping_ai(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    fake_client = FakeClient(
        {"candidates": [{"content": {"parts": [{"text": "4"}]}}]}
    )
    monkeypatch.setattr(openrouter.httpx, "Client", lambda timeout: fake_client)
    assert openrouter.ping_ai() == "4"


def test_ask_ai_retries_then_succeeds(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    fake_client = FakeClient(
        [
            ({}, 503),
            ({}, 503),
            (
                {
                    "candidates": [
                        {
                            "content": {
                                "parts": [
                                    {
                                        "text": json.dumps(
                                            {
                                                "assistant_reply": "Recovered",
                                                "updated_board": None,
                                            }
                                        )
                                    }
                                ]
                            }
                        }
                    ]
                },
                200,
            ),
        ]
    )
    monkeypatch.setattr(openrouter.httpx, "Client", lambda timeout: fake_client)
    monkeypatch.setattr(openrouter.time, "sleep", lambda _: None)
    board = BoardData(columns=[], cards={})
    result = openrouter.ask_ai(board, [], "hello")
    assert result.assistant_reply == "Recovered"
    assert len(fake_client.calls) == 3


def test_ask_ai_raises_sanitized_error_after_retries(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    fake_client = FakeClient([({}, 503), ({}, 503), ({}, 503), ({}, 503)])
    monkeypatch.setattr(openrouter.httpx, "Client", lambda timeout: fake_client)
    monkeypatch.setattr(openrouter.time, "sleep", lambda _: None)
    board = BoardData(columns=[], cards={})
    with pytest.raises(openrouter.AIProviderError) as error:
        openrouter.ask_ai(board, [], "hello")
    assert "temporarily unavailable" in str(error.value).lower()
