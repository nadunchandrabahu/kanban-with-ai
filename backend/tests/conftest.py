from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import db
from app.main import app
from app.models import AIResult, BoardData, Column
import app.openrouter as openrouter


@pytest.fixture()
def temp_db_path(tmp_path: Path) -> Path:
    path = tmp_path / "test.db"
    db.DATABASE_PATH = path
    return path


@pytest.fixture()
def client(temp_db_path: Path) -> TestClient:
    _ = temp_db_path
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def mocked_client_with_ai(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    _ = client

    def fake_ask_ai(board: BoardData, history, user_message: str) -> AIResult:
        _ = board, history, user_message
        return AIResult(assistant_reply="AI reply", updated_board=None)

    monkeypatch.setattr(openrouter, "ask_ai", fake_ask_ai)
    return client


@pytest.fixture()
def mocked_client_with_ai_board_update(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
    _ = client

    def fake_ask_ai(board: BoardData, history, user_message: str) -> AIResult:
        _ = history, user_message
        next_board = board.model_copy(deep=True)
        next_board.columns.append(Column(id="col-new", title="New Column", cardIds=[]))
        return AIResult(assistant_reply="Updated.", updated_board=next_board)

    monkeypatch.setattr(openrouter, "ask_ai", fake_ask_ai)
    return client


@pytest.fixture()
def mocked_client_with_ping(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    _ = client
    monkeypatch.setattr(openrouter, "ping_ai", lambda: "4")
    return client


@pytest.fixture()
def mocked_client_with_ai_provider_error(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
    _ = client

    def fail_ai(board: BoardData, history, user_message: str):
        _ = board, history, user_message
        raise openrouter.AIProviderError(
            "Gemini service is temporarily unavailable. Please try again.",
            provider_status_code=503,
        )

    monkeypatch.setattr(openrouter, "ask_ai", fail_ai)
    return client
