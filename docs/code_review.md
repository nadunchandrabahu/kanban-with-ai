# Code Review

Date: 2026-11-10
Scope: entire repository (backend, frontend, Docker, scripts, tests, docs) at commit `79900f9`.

## Summary

The MVP works end to end: all suites pass (backend 16 tests / 87% coverage, frontend 11 unit / 82% lines, 3 E2E), the Docker image builds, and a live Gemini round-trip creates and persists a card. The code is small and readable.

The main problems are:

1. Data does not survive a Docker restart, which breaks a stated success criterion.
2. A failed board/history load after sign-in shows hardcoded demo data, and the next edit overwrites the user's real board with it (reproduced).
3. The board is saved on every keystroke and from inside a React state updater, and the AI can overwrite edits made while a chat request is in flight.
4. Nothing checks that a board is internally consistent, even though the AI rewrites the whole board.
5. Cards cannot be edited from the UI, which is a stated business requirement.

## Status (2026-11-10)

All High and Medium items are fixed. Low items are still open, plus one new finding (L30).

| Item | Fix | Proof |
|---|---|---|
| H1 | `-v pm-data:/app/data` in both start scripts | Live: AI-added card and chat history still present after `stop.ps1` removed the container and `start.ps1` recreated it |
| H2 | Board shown only after board and history load; `initialData` moved to `src/test/fixtures.ts` | Unit: history 500 keeps the login screen with the error and sends no PUT |
| H3 | Edit / Save / Cancel on each card | Unit, E2E, and live browser against Docker: edit survives reload |
| H4 | `BoardData.check_consistency` validator | 5 parametrized API tests; live PUT with dangling id returns 422; inconsistent AI board returns 502 and leaves the board and history unchanged |
| M1 | Uncontrolled title input, saves on blur/Enter, empty reverts | Unit tests; live browser: 12 typed characters sent 0 PUTs, Enter sent 1 |
| M2 | Save moved out of the state updater; reload on failure | Unit: exactly 1 PUT per edit under `<StrictMode>`; failed save shows the error and restores the server board |
| M3 | Board locked (`aria-busy`, disabled controls, guard in `applyBoardUpdate`) while chat is in flight | Unit: no PUT when trying to edit during a pending chat; unlocks after the reply |
| M4 | `_response_text` raises `AIProviderError`; `responseJsonSchema` from `AIResult`; parsing via `model_validate_json` | API tests for blocked prompt, missing content, non-JSON and non-object replies (all 502); live Gemini call accepted the schema |
| M5 | `SYSTEM_INSTRUCTION` documents board rules; board sent in the final user turn after history | Request-shape unit test; live chat added a card and moved another while keeping all 6 cards consistent |
| M6 | CORS restricted to `localhost:3000` / `127.0.0.1:3000`, no credentials | Unit test and live preflight: no `Access-Control-Allow-Origin` for other origins |
| M7 | `pythonpath = ["."]` | `uv run --extra dev pytest` passes in a clean container |
| M8 | `uv.lock` committed; Dockerfile uses pinned uv and `uv sync --frozen --no-dev`; `.dockerignore` excludes `backend/.venv` | `uv lock --check` passes; Docker build installs from the lock |
| M9 | Tests added | Backend 16 -> 33 tests (90% coverage); frontend unit 11 -> 25 (93% lines); E2E 3 -> 4 |

While fixing H3, the new E2E test caught an accessibility bug that jsdom missed: a disabled `useSortable` sets `aria-disabled` on the card, so the edit inputs were reported as disabled. The fix leaves the drag attributes off while a card is being edited.

Severity: **High** = data loss or broken requirement, **Medium** = real bug or risk with a narrower trigger, **Low** = cleanup, simplification, hygiene.

---

## High

### H1. Board and chat data are lost on every restart in Docker

- **Where:** `scripts/start.ps1:11`, `scripts/start.sh:10`, `scripts/stop.*`, `Dockerfile` (`DATABASE_PATH=/app/data/pm.db`)
- **Problem:** The DB lives in the container filesystem with no volume mounted. The stop scripts remove the container, and the start scripts recreate it, so every stop/start resets to the seeded board and empty chat. `docs/PLAN.md` Part 5 success criterion "Board and chat state survive process restarts" is not met in the only supported deployment.
- **Action:** Mount a named volume in both start scripts: `-v pm-data:/app/data`.

### H2. Failed load after sign-in shows the demo board and then overwrites the real board

- **Where:** `frontend/src/components/KanbanBoard.tsx:83-94`, `:41`, `frontend/src/lib/kanban.ts:18`
- **Problem:** `setAuth(credentials)` runs before the board and history are fetched. If either fetch fails, the board view is already showing, `board` is still the hardcoded `initialData`, and the error goes to `authError`, which is only rendered on the login screen. Any edit then PUTs the demo board over the user's real board. Reproduced with a probe test: history returned 500, the UI showed "Backlog / In Progress / Review / Done" demo data instead of the server board, no error was visible, and "Add column" sent a PUT containing the demo board. The same window exists during a normal login: the demo board is interactive while "Loading board..." is shown. Note the frontend demo cards ("Align roadmap themes") also differ from the backend seed ("Define Q1 goals").
- **Action:** Call `setAuth` only after both fetches succeed. Hold `board` as `BoardData | null` and render the board only when loaded. Delete `initialData` from `kanban.ts` (move it into test fixtures), so the backend seed is the single source of the default board.

### H3. Cards cannot be edited in the UI

- **Where:** `frontend/src/components/KanbanCard.tsx`
- **Problem:** `AGENTS.md` requires that cards "can be moved with drag and drop, and edited". Cards can only be added, removed and moved; title/details can only be changed through the AI chat.
- **Action:** Add an inline edit (click title/details to edit, save on blur or Enter) that calls a new `handleEditCard` through `applyBoardUpdate`. Add a unit test.

### H4. No check that the board is consistent; the AI can corrupt it

- **Where:** `backend/app/models.py:16-18`, `backend/app/openrouter.py:68-72`, `backend/app/main.py:73-75`
- **Problem:** `BoardData` validates shape only. The AI returns a full replacement board, and nothing checks that every `cardIds` entry exists in `cards`, that no card id appears twice, that every card belongs to exactly one column, or that `cards[key].id == key`. The frontend hides dangling ids (`KanbanBoard.tsx:324-330`), so orphan cards accumulate silently, and duplicate ids break `@dnd-kit` sortable contexts. The same applies to `PUT /api/board`.
- **Action:** Add a `model_validator(mode="after")` on `BoardData` that enforces those rules (it covers both the PUT route and AI output, since both validate through `BoardData`). Invalid AI output then becomes a 502 instead of corrupt saved data. Add tests for each rule.

---

## Medium

### M1. Column rename saves on every keystroke and cannot be cleared

- **Where:** `frontend/src/components/KanbanColumn.tsx:46-50`, `KanbanBoard.tsx:36`, `:124-131`
- **Problem:** `onChange` calls `onRename`, which PUTs the whole board per keystroke. Parallel PUTs can be processed out of order, so the saved title can end up stale. `safeColumnTitle` turns an empty value into "Untitled" immediately, so clearing the field to retype is impossible (confirmed: clearing the input leaves "Untitled").
- **Action:** Keep the draft title in local state in `KanbanColumn` and call `onRename` on blur / Enter. Apply the "Untitled" fallback only at commit.

### M2. Network call inside a React state updater

- **Where:** `frontend/src/components/KanbanBoard.tsx:60-71`
- **Problem:** `saveBoard` is called inside the `setBoard(prev => ...)` updater. Updaters must be pure; React StrictMode (on by default in Next.js dev) runs them twice, so each edit sends two PUTs in dev. A failed save leaves the UI diverged from the server with only an error string.
- **Action:** Compute `next` from the current `board` value, call `setBoard(next)`, then `saveBoard(auth, next)` outside the updater. On failure, show the error and reload the board from the server.

### M3. AI reply overwrites edits made during a chat request

- **Where:** `backend/app/main.py:55-82`, `KanbanBoard.tsx:206-210`
- **Problem:** The backend snapshots the board when the chat request arrives (Gemini can take several seconds, up to minutes with retries). Edits saved in that window are overwritten when the AI's full board is saved and then replaces client state.
- **Action:** Simplest fix: disable board editing while `sendingChat` is true (for example, a `pointer-events-none opacity-60` wrapper on the board section and disabled buttons). Note the limitation in the AI sidebar copy.

### M4. Gemini responses without candidates or with non-object JSON cause 500s

- **Where:** `backend/app/openrouter.py:68-72`, `:137-138`, `:147`
- **Problem:** `data["candidates"][0]["content"]["parts"][0]["text"]` raises `KeyError`/`IndexError` when Gemini blocks a prompt or returns no content (it returns `promptFeedback` or a candidate with no `content`). If the model returns a JSON array or string, `payload.get` raises `AttributeError`. None of these are caught in `main.py`, so the user gets a generic 500 instead of the 502 used for other provider failures.
- **Action:** Add a `_response_text(data)` helper that raises `AIProviderError("Gemini returned no content.")` when the path is missing. Also pass a `responseSchema` in `generationConfig` (Gemini supports structured output), which removes most parse failures and the need for `_extract_json_payload`. Test both cases.

### M5. AI prompt does not describe the board schema

- **Where:** `backend/app/openrouter.py:117-129`
- **Problem:** The system instruction does not explain the board shape (columns own ordering via `cardIds`, cards are a map keyed by id, new ids must be unique, keep every existing card unless asked to delete). Correctness relies on the model inferring it from the JSON. The current board is also sent as the first message, before the history, so the model reads stale conversation after the current state.
- **Action:** Describe the schema and rules in the system instruction (or rely on `responseSchema` from M4). Put the current board in the final user turn together with the new message.

### M6. Open CORS lets any website use the API with the known default credentials

- **Where:** `backend/app/main.py:14-20`
- **Problem:** `allow_origins=["*"]` plus hardcoded, publicly known credentials (`user` / `password`) means any page the user visits can read and overwrite the board at `localhost:8000` and spend Gemini quota through `/api/chat`. In production the app is single-origin, so CORS is not needed at all.
- **Action:** Remove the middleware, or restrict it to the dev origin (`http://localhost:3000`) only when `NEXT_PUBLIC_API_BASE` is used. Drop `allow_credentials=True`, since auth uses headers, not cookies.

### M7. Documented backend test command fails on a clean checkout

- **Where:** `backend/pyproject.toml`, `CLAUDE.md`
- **Problem:** `uv run --extra dev pytest` fails with `ModuleNotFoundError: No module named 'app'`, because plain `pytest` does not put `backend/` on `sys.path` and the project has no build system, so uv does not install it. It only works where the package was pip-installed earlier (there is a stale `pm_backend.egg-info`). Verified in a clean `python:3.12-slim` container.
- **Action:** Add `pythonpath = ["."]` under `[tool.pytest.ini_options]`.

### M8. Unpinned Python dependencies

- **Where:** `Dockerfile:11-14`, `backend/pyproject.toml`
- **Problem:** There is no `uv.lock`, and the image installs with `pip install uv` + `uv pip install --system .`, so every build resolves the latest compatible versions. Builds are not reproducible (a new Starlette version already emits deprecation warnings).
- **Action:** Run `uv lock`, commit `uv.lock`, and in the Dockerfile use `uv sync --frozen --no-dev` (copy `pyproject.toml` and `uv.lock` first, so the dependency layer is cached).

### M9. Test gaps against the plan

- **Backend:** no test for malformed board payload rejection (Part 6 lists it), chat without auth, invalid/unparseable AI output, missing API key at the route level, or the consistency rules from H4.
- **Frontend:** no tests for the chat sidebar (send, render, error, board replacement from `board_updated`), which Part 10 lists. No tests for login failure, logout, column add/remove/rename, or the failure path from H2. `KanbanBoard.tsx` is at 71% line / 44% function coverage.
- **Action:** Add those tests along with the fixes above.

---

## Low

### Backend

- **L1.** `openrouter.py:23-30`: the client module raises FastAPI `HTTPException` for a missing key. Raise `AIProviderError` instead, and let `main.py` own HTTP mapping (it becomes a 502 with a clear message).
- **L2.** `openrouter.py:33-34`: the API key goes in the URL query string. Send it as the `x-goog-api-key` header so it cannot leak through URL logging (httpx logs request URLs at INFO).
- **L3.** `openrouter.py:83-105`: `last_error` and the final `raise` after the loop are unreachable; remove them. `_headers()` is a one-line constant; inline it.
- **L4.** `openrouter.py`: file name is misleading after the Gemini switch. Rename to `gemini.py` (update imports, monkeypatch targets and docs together).
- **L5.** `db.py:13-56`: `ColumnLike` / `CardLike` are PascalCase functions returning dicts. Use plain dict literals or the `Column` / `Card` models.
- **L6.** `db.py:144-161`: the "no board row, insert default" branch duplicates seeding in `init_db`, and the `ValueError("User not found.")` branches in four functions cannot happen after `require_username`. Remove both (this also removes most of the uncovered lines).
- **L7.** `db.py:218`: `database_path()` is unused; remove it.
- **L8.** `main.py:23`: `@app.on_event("startup")` is deprecated; use a `lifespan` handler.
- **L9.** `main.py:102-121`: when the frontend build is missing, the catch-all route also captures unknown `/api/...` paths and returns 500 instead of 404. Acceptable for MVP; if kept, limit it to non-`/api` paths.
- **L10.** `main.py:91-93`: `ai_ping` assigns `_ = username` just to silence lint; use `dependencies=[Depends(require_username)]` on the route instead.
- **L11.** `models.py:31-32`: `ChatRequest.message` has no maximum length; add `max_length` (for example 4000) to bound prompt size and cost.
- **L12.** Passwords are stored and compared in plain text. Acceptable for the hardcoded MVP user. Note it in `docs/DATABASE.md` as a known limitation before adding real users.

### Frontend

- **L13.** `KanbanBoard.tsx:58`: `useMemo(() => board.cards, [board.cards])` does nothing; use `board.cards` directly.
- **L14.** `kanban.ts:144-148`: `createId` uses `Math.random`; use `crypto.randomUUID()`.
- **L15.** `api.ts:27-33`: errors surface the raw response body (for example `{"detail":"Invalid credentials."}`). Parse `detail` when present.
- **L16.** `KanbanBoard.tsx:203`: when chat fails, the user message stays in the list but was never saved on the server, so it disappears on the next login. Remove it on failure, or keep the input text so the user can retry.
- **L17.** `KanbanBoard.tsx:141-160`: removing a column deletes all its cards with no confirmation. Add a `window.confirm` when the column has cards.
- **L18.** Drag-and-drop has no `KeyboardSensor`, so it is mouse-only. Add `useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })`.
- **L19.** `KanbanBoard.tsx:101-106`: logout leaves `chatInput`, `chatError` and `boardError` in place. Reset them, or remount the component by key.

### Build, scripts, repo hygiene

- **L20.** Start/stop scripts use relative paths (`.`, `.env`) and only work from the repo root. `cd` to the script's parent directory first (`$PSScriptRoot\..` / `"$(dirname "$0")/.."`).
- **L21.** `frontend/test-results/.last-run.json` is committed. Add `/test-results/` and `/playwright-report/` to `frontend/.gitignore`, and remove the file from git.
- **L22.** ESLint lints the generated `frontend/coverage/` report (one warning today). Add `"coverage/**"` to `globalIgnores` in `eslint.config.mjs`.
- **L23.** `.dockerignore` does not exclude `backend/.venv`, `frontend/out` or `frontend/coverage`; a local `.venv` would be copied into the image by `COPY backend/`. Add them.
- **L24.** The Docker image runs as root and has no `HEALTHCHECK`. Fine for a local MVP; add a non-root user and `HEALTHCHECK` against `/api/health` if it is ever deployed.
- **L25.** Frontend scaffold leftovers: `frontend/public/*.svg` (Next.js template assets) are unused, and `frontend/README.md` still describes running the standalone frontend. Remove the unused files; reduce the README to the actual commands.

### Documentation

- **L26.** `docs/PLAN.md`: every checkbox is unchecked although all 10 parts are implemented, and Parts 1, 8 and 9 still say OpenRouter. Tick completed items and replace OpenRouter with Gemini.
- **L27.** `AGENTS.md` says columns are "fixed" and can only be renamed, but the plan and code support adding and removing columns. Make them agree (decide which is intended).
- **L28.** `frontend/AGENTS.md` describes the original in-memory demo; update it for API-backed state, the login gate and the chat sidebar.
- **L29.** No root `README.md`. Add a minimal one (start/stop commands, `.env` with `GEMINI_API_KEY`, login credentials).
- **L30.** (Found during fixes.) `npx tsc --noEmit` reports errors in every test file (`vi`, `describe`, `expect` not found), because the Vitest globals types are not included in `tsconfig.json`. This existed before the fixes; app source has no type errors. Add `"types": ["vitest/globals", "@testing-library/jest-dom"]` to `compilerOptions`, or import from `vitest` explicitly.

---

## Action plan (suggested order)

1. **Data safety:** H1 (volume), H2 (login/load flow, remove `initialData`), M2 (pure updater), M1 (rename on commit).
2. **AI robustness:** H4 (board consistency validator), M4 (missing content, `responseSchema`), M5 (prompt and message order), M3 (lock board during chat).
3. **Requirement gap:** H3 (card editing).
4. **Security and tooling:** M6 (CORS), M7 (pytest pythonpath), M8 (`uv.lock`), L1-L2 (key handling).
5. **Tests:** M9, written alongside steps 1-3.
6. **Cleanup and docs:** remaining Low items, then update `PLAN.md`, `AGENTS.md`, `frontend/AGENTS.md`, `CLAUDE.md` and `DATABASE.md` to match.

## What is in good shape

- Small, readable modules with a clear split (routes, DB, auth, AI client, models).
- Parameterized SQL throughout; no injection risk.
- Provider errors are sanitized before reaching the client, and there is a test that the API key never appears in error details.
- Retry with exponential backoff on 429/5xx.
- Chat messages are persisted only after a successful AI call.
- Pure drag logic (`moveCard`) is separated from the component and unit tested.
- Coverage gates are enforced on both suites; E2E tests are hermetic (all `/api/**` stubbed).
