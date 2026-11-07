# Project Execution Plan

This plan is implementation-first and will proceed continuously. The MVP target is:

- FastAPI backend with SQLite persistence (per-user board + chat history)
- Static NextJS frontend served by FastAPI
- Dummy login (`user` / `password`) with frontend state and backend verification per request
- Kanban with 4 starter columns; add/remove columns supported
- AI sidebar chat via OpenRouter with structured output for optional board updates
- Minimum 80% unit test coverage and robust integration tests

## Part 1: Planning and project docs

- [ ] Expand implementation plan and quality gates in this file
- [ ] Add `frontend/AGENTS.md` summarizing the existing frontend architecture
- [ ] Keep `backend/AGENTS.md` and `scripts/AGENTS.md` aligned with implemented structure

Tests:
- [ ] Doc sanity review: verify each part has tasks, tests, and success criteria

Success criteria:
- [ ] A new contributor can implement and validate the MVP by following only docs

## Part 2: Scaffolding (container, backend skeleton, scripts)

- [ ] Add Python project config in `backend/` with `uv`-managed dependencies
- [ ] Add FastAPI app bootstrap and health endpoint
- [ ] Add Dockerfile that builds frontend static assets and runs FastAPI
- [ ] Add start/stop scripts for Windows, Mac, and Linux in `scripts/`

Tests:
- [ ] Backend app import and health route tests pass
- [ ] Local script run starts app and reaches `/api/health`

Success criteria:
- [ ] `docker build` succeeds and app starts with one command
- [ ] `/api/health` returns success JSON

## Part 3: Static frontend served by FastAPI

- [ ] Configure frontend build for static export
- [ ] Mount exported frontend under `/` in FastAPI
- [ ] Ensure static assets resolve correctly in container

Tests:
- [ ] Integration test: root `/` returns HTML payload
- [ ] E2E smoke test loads board shell from served app

Success criteria:
- [ ] Visiting `/` from backend process shows the frontend UI

## Part 4: Fake sign-in UX

- [ ] Add login screen gate before board access
- [ ] Implement frontend auth state and logout flow
- [ ] Verify credentials with backend endpoint on each protected request

Tests:
- [ ] Frontend unit tests for login success/failure and logout behavior
- [ ] Backend tests for credential verification endpoint

Success criteria:
- [ ] Only valid credentials unlock board UI
- [ ] Logout returns user to login screen

## Part 5: Database model and persistence

- [ ] Create SQLite schema with tables for users, boards, and chat messages
- [ ] Persist board as JSON per user (MVP simplicity)
- [ ] Seed default user and default board with 4 columns when missing
- [ ] Document DB approach in `docs/DATABASE.md`

Tests:
- [ ] Unit tests for schema init and first-run bootstrap
- [ ] Unit tests for board load/save behavior

Success criteria:
- [ ] Database auto-creates on first start
- [ ] Board and chat state survive process restarts

## Part 6: Backend API for Kanban

- [ ] Add authenticated board read endpoint
- [ ] Add board update endpoint with validation
- [ ] Support column and card ordering persistence through API payload

Tests:
- [ ] Integration tests for read/update flow with auth pass/fail cases
- [ ] Validation tests for malformed board payload rejection

Success criteria:
- [ ] Every board edit in UI can be persisted via backend API

## Part 7: Frontend wired to backend

- [ ] Replace in-memory board with API-backed state
- [ ] Add loading/error states for board fetch and save
- [ ] Keep drag-and-drop and editing interactions intact
- [ ] Add column add/remove UI and persistence

Tests:
- [ ] Frontend unit/integration tests for API-backed board interactions
- [ ] Integration tests for end-to-end login + board persistence

Success criteria:
- [ ] Refreshing page preserves board exactly as last saved

## Part 8: AI connectivity

- [ ] Add OpenRouter client in backend
- [ ] Add connectivity test path using simple prompt (`2+2`)
- [ ] Add guarded error handling for missing API key or upstream errors

Tests:
- [ ] Unit tests for request construction and response parsing (mocked HTTP)
- [ ] Integration test for AI connectivity route with mocked transport

Success criteria:
- [ ] Backend can successfully complete a minimal AI round-trip

## Part 9: Structured AI board operations

- [ ] Define strict structured response schema: assistant reply + optional board patch/update
- [ ] Send board JSON + user prompt + persisted conversation history to model
- [ ] Validate model output server-side and persist accepted board updates

Tests:
- [ ] Unit tests for schema validation, invalid-output handling, and apply-update logic
- [ ] Integration tests for chat endpoint with and without board updates

Success criteria:
- [ ] AI responses are consistently parseable
- [ ] Optional board updates apply safely and persist

## Part 10: AI sidebar in frontend

- [ ] Build sidebar chat UI with message history
- [ ] Send user prompts to backend and render assistant responses
- [ ] Apply backend-returned board updates and refresh board state automatically

Tests:
- [ ] Frontend tests for chat send/render/error states
- [ ] Integration tests proving board changes after AI-directed update

Success criteria:
- [ ] User can chat in sidebar and see board auto-refresh after AI updates

## Quality gates for done state

- [ ] Unit coverage >= 80% across backend + frontend test suites
- [ ] Integration tests pass for auth, persistence, and AI route behavior
- [ ] Dockerized app starts and serves full MVP at `/`
