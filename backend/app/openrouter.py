from __future__ import annotations

import os
import time

import httpx
from fastapi import HTTPException, status

from app.config import GEMINI_BASE_URL, MODEL_NAME
from app.models import AIResult, BoardData, ChatMessage

RETRY_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_RETRIES = 3


class AIProviderError(Exception):
    def __init__(self, message: str, provider_status_code: int | None = None):
        super().__init__(message)
        self.provider_status_code = provider_status_code


def _api_key() -> str:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GEMINI_API_KEY is missing.",
        )
    return key


def _url() -> str:
    return f"{GEMINI_BASE_URL}/{MODEL_NAME}:generateContent?key={_api_key()}"


def _headers() -> dict[str, str]:
    return {"Content-Type": "application/json"}


def _safe_provider_error(error: httpx.HTTPStatusError) -> AIProviderError:
    code = error.response.status_code
    if code == 503:
        return AIProviderError(
            "Gemini service is temporarily unavailable. Please try again.",
            provider_status_code=code,
        )
    if code == 429:
        return AIProviderError(
            "Gemini rate limit reached. Please try again shortly.",
            provider_status_code=code,
        )
    return AIProviderError(
        f"Gemini request failed with status {code}.",
        provider_status_code=code,
    )


SYSTEM_INSTRUCTION = """You are a project management assistant for a Kanban board.
Respond with JSON matching the response schema: assistant_reply (short plain text) and updated_board.

Board format:
- columns: ordered list of {id, title, cardIds}. cardIds lists that column's card ids, top to bottom.
- cards: object mapping each card id to {id, title, details}. The key must equal the card's id.

Rules for updated_board:
- Set it to null unless the user asked you to change the board.
- When changing the board, return the complete board, not only the changes.
- Keep every existing column and card exactly as it is unless the user asked to change or delete it.
- Every card must appear in exactly one column's cardIds, and every id in cardIds must exist in cards.
- Give new cards and columns new unique ids, such as card-<short random suffix>."""


def _response_text(data: dict) -> str:
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as error:
        raise AIProviderError("Gemini returned no content.") from error


def _parse_response_content(content: str) -> AIResult:
    return AIResult.model_validate_json(content)


def _history_to_gemini_contents(history: list[ChatMessage]) -> list[dict]:
    contents: list[dict] = []
    for item in history[-20:]:
        role = "user" if item.role == "user" else "model"
        contents.append({"role": role, "parts": [{"text": item.content}]})
    return contents


def _post_with_retry(body: dict, timeout_seconds: float) -> dict:
    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            with httpx.Client(timeout=timeout_seconds) as client:
                response = client.post(_url(), headers=_headers(), json=body)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as error:
            last_error = error
            status_code = error.response.status_code
            if status_code in RETRY_STATUS_CODES and attempt < MAX_RETRIES:
                time.sleep(0.4 * (2**attempt))
                continue
            raise _safe_provider_error(error) from error
        except httpx.HTTPError as error:
            last_error = error
            if attempt < MAX_RETRIES:
                time.sleep(0.4 * (2**attempt))
                continue
            raise AIProviderError("Gemini request could not be completed.") from error
    raise AIProviderError("Gemini request could not be completed.") from last_error


def ask_ai(
    board: BoardData,
    history: list[ChatMessage],
    user_message: str,
) -> AIResult:
    prompt = f"Current board JSON:\n{board.model_dump_json()}\n\nUser request:\n{user_message}"
    body = {
        "systemInstruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
        "contents": [
            *_history_to_gemini_contents(history),
            {"role": "user", "parts": [{"text": prompt}]},
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseJsonSchema": AIResult.model_json_schema(),
        },
    }
    data = _post_with_retry(body=body, timeout_seconds=45.0)
    return _parse_response_content(_response_text(data))


def ping_ai() -> str:
    body = {
        "contents": [
            {"role": "user", "parts": [{"text": "What is 2+2? Reply with one token."}]}
        ],
    }
    data = _post_with_retry(body=body, timeout_seconds=30.0)
    return _response_text(data)
