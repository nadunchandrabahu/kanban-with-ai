from __future__ import annotations

import json
import os

import httpx
from fastapi import HTTPException, status

from app.config import MODEL_NAME, OPENROUTER_URL
from app.models import AIResult, BoardData, ChatMessage


SCHEMA = {
    "name": "kanban_chat_response",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "assistant_reply": {"type": "string"},
            "updated_board": {
                "anyOf": [
                    {"type": "null"},
                    {
                        "type": "object",
                        "properties": {
                            "columns": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "string"},
                                        "title": {"type": "string"},
                                        "cardIds": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                    },
                                    "required": ["id", "title", "cardIds"],
                                    "additionalProperties": False,
                                },
                            },
                            "cards": {
                                "type": "object",
                                "additionalProperties": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "string"},
                                        "title": {"type": "string"},
                                        "details": {"type": "string"},
                                    },
                                    "required": ["id", "title", "details"],
                                    "additionalProperties": False,
                                },
                            },
                        },
                        "required": ["columns", "cards"],
                        "additionalProperties": False,
                    },
                ]
            },
        },
        "required": ["assistant_reply", "updated_board"],
        "additionalProperties": False,
    },
}


def _headers() -> dict[str, str]:
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OPENROUTER_API_KEY is missing.",
        )
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _parse_response_content(content: str) -> AIResult:
    payload = json.loads(content)
    if payload.get("updated_board") is not None:
        payload["updated_board"] = BoardData.model_validate(payload["updated_board"])
    return AIResult.model_validate(payload)


def ask_ai(
    board: BoardData,
    history: list[ChatMessage],
    user_message: str,
) -> AIResult:
    messages = [
        {
            "role": "system",
            "content": (
                "You are a project management assistant. Reply with practical advice. "
                "Only provide updated_board when the user requested concrete board changes. "
                "When providing updated_board, return the full board object."
            ),
        },
        {
            "role": "system",
            "content": f"Current board JSON: {board.model_dump_json()}",
        },
    ]
    for item in history[-20:]:
        messages.append({"role": item.role, "content": item.content})
    messages.append({"role": "user", "content": user_message})

    body = {
        "model": MODEL_NAME,
        "messages": messages,
        "response_format": {"type": "json_schema", "json_schema": SCHEMA},
    }
    with httpx.Client(timeout=45.0) as client:
        response = client.post(OPENROUTER_URL, headers=_headers(), json=body)
    response.raise_for_status()
    data = response.json()
    content = data["choices"][0]["message"]["content"]
    return _parse_response_content(content)


def ping_ai() -> str:
    body = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": "What is 2+2? Reply with one token."}],
    }
    with httpx.Client(timeout=30.0) as client:
        response = client.post(OPENROUTER_URL, headers=_headers(), json=body)
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]
