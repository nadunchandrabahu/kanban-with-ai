# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Project requirements, technical decisions, color scheme and coding standards are in @AGENTS.md. Follow them: keep it simple, no over-engineering, no emojis, prove root causes before fixing. Planning docs live in `docs/` (`docs/PLAN.md`, `docs/DATABASE.md`).

## Commands

Full app (Docker, port 8000, reads `.env` for `GEMINI_API_KEY`):
- Windows: `scripts/start.ps1` / `scripts/stop.ps1` (or `.cmd` wrappers)
- Mac/Linux: `scripts/start.sh` / `scripts/stop.sh`

Backend (run from `backend/`; there is no lockfile, use the `dev` extra):
- Tests: `uv run --extra dev pytest`
- Single test: `uv run --extra dev pytest tests/test_api.py::test_name --no-cov`. Pass `--no-cov`, because pyproject adds `--cov-fail-under=80`, so a partial run otherwise fails on coverage.
- Dev server: `uv run uvicorn app.main:app --reload`. The backend does not load `.env` itself, so export `GEMINI_API_KEY` first.

Frontend (run from `frontend/`):
- `npm run dev`, `npm run build` (static export to `frontend/out`), `npm run lint`
- Unit tests (Vitest): `npm run test:unit`, single file: `npx vitest run src/lib/kanban.test.ts`, coverage: `npm run test:coverage`
- E2E (Playwright, starts its own `next dev` on port 3400): `npm run test:e2e`

Both suites enforce coverage thresholds of about 80%.

## Architecture

**Single origin in production.** The Dockerfile builds the Next.js app as a static export (`output: "export"`), copies `frontend/out` into the Python image, and FastAPI mounts it at `/` with `StaticFiles`. The mount is decided at import time in `backend/app/main.py`: if `FRONTEND_DIST` does not exist, a catch-all route returns 500 instead. Paths come from env vars `FRONTEND_DIST` and `DATABASE_PATH` (`backend/app/config.py`), which default to `frontend/out` and `data/pm.db` locally. The frontend calls relative `/api/...` URLs; set `NEXT_PUBLIC_API_BASE` to point `next dev` at a separately running backend (CORS is open).

**Auth is stateless.** There are no sessions or tokens. The frontend keeps the credentials in React state (lost on refresh) and sends them as `x-username` / `x-password` headers on every request. The `require_username` dependency (`backend/app/auth.py`) checks them against the `users` table.

**Board is one JSON blob per user.** `{ columns: [{id, title, cardIds[]}], cards: {id: {id, title, details}} }`. Columns hold the ordering, and cards are a lookup map. The shape is defined twice and must stay in sync: pydantic in `backend/app/models.py` and TypeScript in `frontend/src/lib/kanban.ts`. The frontend saves optimistically: every edit goes through `applyBoardUpdate` in `KanbanBoard.tsx`, which PUTs the entire board. The DB is created and seeded (default user plus a 4-column board) by `db.init_db()` on startup.

**AI chat** (`POST /api/chat`): the backend sends the current board JSON, the last 20 persisted messages and the new prompt to Gemini via raw `httpx` (no SDK), with `responseMimeType: application/json`. The model returns `{assistant_reply, updated_board}`. When `updated_board` is present, it is the full replacement board; it is validated with pydantic, saved, and returned so the frontend can replace its state. Chat messages are persisted only after a successful AI call. Provider failures map to `AIProviderError` and then to HTTP 502. Despite the filename, `backend/app/openrouter.py` is the Gemini client (the project moved from OpenRouter to Gemini).

**Frontend is essentially one component.** `frontend/src/components/KanbanBoard.tsx` holds the login gate, board state, `@dnd-kit` drag-and-drop and the chat sidebar. Pure drag logic lives in `moveCard` in `frontend/src/lib/kanban.ts`, and all fetch calls are in `frontend/src/lib/api.ts`.

## Testing conventions

- Backend tests point `db.DATABASE_PATH` at a temp file and monkeypatch `openrouter.ask_ai` / `openrouter.ping_ai` (fixtures in `backend/tests/conftest.py`). `main.py` calls these through the module (`openrouter.ask_ai(...)`), so keep that style; a `from app.openrouter import ask_ai` import would bypass the mocks.
- Playwright tests stub every `/api/**` call with `page.route`, so they run against `next dev` only and need no backend.
