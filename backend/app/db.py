from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from app.config import DATABASE_PATH, DEFAULT_PASSWORD, DEFAULT_USERNAME
from app.models import BoardData, ChatMessage


def default_board() -> BoardData:
    return BoardData(
        columns=[
            ColumnLike("col-backlog", "Backlog", ["card-1", "card-2"]),
            ColumnLike("col-progress", "In Progress", ["card-3"]),
            ColumnLike("col-review", "Review", ["card-4"]),
            ColumnLike("col-done", "Done", ["card-5"]),
        ],
        cards={
            "card-1": CardLike(
                "card-1",
                "Define Q1 goals",
                "Align stakeholders on measurable outcomes.",
            ),
            "card-2": CardLike(
                "card-2",
                "Collect customer pain points",
                "Review support trends and top blockers.",
            ),
            "card-3": CardLike(
                "card-3",
                "Implement API scaffolding",
                "Create health endpoint and board routes.",
            ),
            "card-4": CardLike(
                "card-4",
                "Test drag and drop",
                "Verify board interactions with integration tests.",
            ),
            "card-5": CardLike(
                "card-5",
                "Publish local MVP",
                "Run app in Docker and confirm startup scripts.",
            ),
        },
    )


def ColumnLike(column_id: str, title: str, card_ids: list[str]) -> dict:
    return {"id": column_id, "title": title, "cardIds": card_ids}


def CardLike(card_id: str, title: str, details: str) -> dict:
    return {"id": card_id, "title": title, "details": details}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_connection() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def open_connection():
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    with open_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              username TEXT NOT NULL UNIQUE,
              password TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS boards (
              user_id INTEGER PRIMARY KEY,
              data TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS chat_messages (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL,
              role TEXT NOT NULL,
              content TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )
        conn.execute(
            """
            INSERT INTO users (username, password)
            VALUES (?, ?)
            ON CONFLICT(username) DO NOTHING
            """,
            (DEFAULT_USERNAME, DEFAULT_PASSWORD),
        )
        user_id = get_user_id(conn, DEFAULT_USERNAME)
        if user_id is not None:
            existing = conn.execute(
                "SELECT user_id FROM boards WHERE user_id = ?", (user_id,)
            ).fetchone()
            if existing is None:
                conn.execute(
                    "INSERT INTO boards (user_id, data, updated_at) VALUES (?, ?, ?)",
                    (user_id, default_board().model_dump_json(), _now()),
                )
        conn.commit()


def get_user_id(conn: sqlite3.Connection, username: str) -> int | None:
    row = conn.execute(
        "SELECT id FROM users WHERE username = ?",
        (username,),
    ).fetchone()
    return None if row is None else int(row["id"])


def verify_credentials(username: str, password: str) -> bool:
    with open_connection() as conn:
        row = conn.execute(
            "SELECT id FROM users WHERE username = ? AND password = ?",
            (username, password),
        ).fetchone()
    return row is not None


def get_board_for_user(username: str) -> BoardData:
    with open_connection() as conn:
        user_id = get_user_id(conn, username)
        if user_id is None:
            raise ValueError("User not found.")
        row = conn.execute(
            "SELECT data FROM boards WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if row is None:
            board = default_board()
            conn.execute(
                "INSERT INTO boards (user_id, data, updated_at) VALUES (?, ?, ?)",
                (user_id, board.model_dump_json(), _now()),
            )
            conn.commit()
            return board
        return BoardData.model_validate(json.loads(row["data"]))


def save_board_for_user(username: str, board: BoardData) -> None:
    with open_connection() as conn:
        user_id = get_user_id(conn, username)
        if user_id is None:
            raise ValueError("User not found.")
        conn.execute(
            """
            INSERT INTO boards (user_id, data, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
              data = excluded.data,
              updated_at = excluded.updated_at
            """,
            (user_id, board.model_dump_json(), _now()),
        )
        conn.commit()


def add_chat_message(username: str, message: ChatMessage) -> None:
    with open_connection() as conn:
        user_id = get_user_id(conn, username)
        if user_id is None:
            raise ValueError("User not found.")
        conn.execute(
            """
            INSERT INTO chat_messages (user_id, role, content, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, message.role, message.content, _now()),
        )
        conn.commit()


def get_chat_history(username: str, limit: int = 30) -> list[ChatMessage]:
    with open_connection() as conn:
        user_id = get_user_id(conn, username)
        if user_id is None:
            raise ValueError("User not found.")
        rows = conn.execute(
            """
            SELECT role, content
            FROM chat_messages
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    return [
        ChatMessage(role=row["role"], content=row["content"])
        for row in reversed(rows)
    ]


def database_path() -> Path:
    return DATABASE_PATH
