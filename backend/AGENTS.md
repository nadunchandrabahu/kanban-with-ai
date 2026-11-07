## Backend Overview

The backend is a FastAPI service that:

- Verifies dummy credentials (`user` / `password`)
- Persists Kanban board state per user in SQLite
- Persists chat history per user in SQLite
- Serves Gemini-backed AI chat with structured board update payloads
- Serves exported frontend static assets from `/`

## Main modules

- `app/main.py`: API routes, startup, and static serving
- `app/db.py`: schema setup and persistence helpers
- `app/auth.py`: request-level credential verification
- `app/openrouter.py`: Gemini integration and structured response parsing
- `app/models.py`: pydantic request/response models

## Tests

- `tests/test_db.py`: database initialization and persistence behavior
- `tests/test_api.py`: auth, board, chat, and AI ping route tests