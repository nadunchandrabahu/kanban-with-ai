from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator


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

    @model_validator(mode="after")
    def check_consistency(self) -> Self:
        column_ids = [column.id for column in self.columns]
        if len(column_ids) != len(set(column_ids)):
            raise ValueError("Column ids must be unique.")
        placed = [card_id for column in self.columns for card_id in column.cardIds]
        if len(placed) != len(set(placed)):
            raise ValueError("Each card must appear in only one column, once.")
        if set(placed) != set(self.cards):
            raise ValueError("Every card must be in exactly one column, and every cardId must exist in cards.")
        for key, card in self.cards.items():
            if card.id != key:
                raise ValueError(f"Card key {key!r} does not match card id {card.id!r}.")
        return self


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
