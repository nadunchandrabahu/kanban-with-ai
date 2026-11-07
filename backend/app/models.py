from typing import Literal
from pydantic import BaseModel, Field


class Card(BaseModel):
    id: str
    title: str = Field(min_length=1)
    details: str = ""


class Column(BaseModel):
    id: str
    title: str = Field(min_length=1)
    cardIds: list[str] = Field(default_factory=list)


class BoardData(BaseModel):
    columns: list[Column] = Field(default_factory=list)
    cards: dict[str, Card] = Field(default_factory=dict)


class Credentials(BaseModel):
    username: str
    password: str


class AuthStatus(BaseModel):
    ok: bool


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)


class ChatResponse(BaseModel):
    message: str
    board_updated: bool
    board: BoardData | None = None


class AIResult(BaseModel):
    assistant_reply: str
    updated_board: BoardData | None = None
