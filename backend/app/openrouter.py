from __future__ import annotations

import json
import os

import httpx
from fastapi import HTTPException, status

from app.config import GEMINI_BASE_URL, MODEL_NAME
from app.models import AIResult, BoardData, ChatMessage


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


def _extract_json_payload(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if len(lines) >= 3:
            cleaned = "\n".join(lines[1:-1]).strip()
    return cleaned


def _parse_response_content(content: str) -> AIResult:
    payload = json.loads(_extract_json_payload(content))
    if payload.get("updated_board") is not None:
        payload["updated_board"] = BoardData.model_validate(payload["updated_board"])
    return AIResult.model_validate(payload)


def _history_to_gemini_contents(history: list[ChatMessage]) -> list[dict]:
    contents: list[dict] = []
    for item in history[-20:]:
        role = "user" if item.role == "user" else "model"
        contents.append({"role": role, "parts": [{"text": item.content}]})
    return contents


def ask_ai(
    board: BoardData,
    history: list[ChatMessage],
    user_message: str,
) -> AIResult:
    body = {
        "systemInstruction": {
            "parts": [
                {
                    "text": (
                        "You are a project management assistant. Reply with practical advice. "
                        "Return strict JSON with keys assistant_reply and updated_board. "
                        "Only provide updated_board when the user requested concrete board changes. "
                        "When providing updated_board, return the full board object."
                    )
                }
            ]
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": f"Current board JSON: {board.model_dump_json()}"}],
            },
            *_history_to_gemini_contents(history),
            {"role": "user", "parts": [{"text": user_message}]},
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
        },
    }
    with httpx.Client(timeout=45.0) as client:
        response = client.post(_url(), headers=_headers(), json=body)
    response.raise_for_status()
    data = response.json()
    content = data["candidates"][0]["content"]["parts"][0]["text"]
    return _parse_response_content(content)


def ping_ai() -> str:
    body = {
        "contents": [
            {"role": "user", "parts": [{"text": "What is 2+2? Reply with one token."}]}
        ],
    }
    with httpx.Client(timeout=30.0) as client:
        response = client.post(_url(), headers=_headers(), json=body)
    response.raise_for_status()
    data = response.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]
