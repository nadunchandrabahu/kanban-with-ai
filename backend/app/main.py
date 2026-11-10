import httpx
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import db, openrouter
from app.auth import require_username
from app.config import FRONTEND_DIST
from app.models import AuthStatus, BoardData, ChatMessage, ChatRequest, ChatResponse, Credentials

app = FastAPI(title="Project Management MVP API")

# Production is single-origin. CORS only exists for `next dev` pointed at this backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    db.init_db()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/auth/verify", response_model=AuthStatus)
def verify_auth(payload: Credentials) -> AuthStatus:
    return AuthStatus(ok=db.verify_credentials(payload.username, payload.password))


@app.get("/api/board", response_model=BoardData)
def get_board(username: str = Depends(require_username)) -> BoardData:
    return db.get_board_for_user(username)


@app.put("/api/board", response_model=BoardData)
def update_board(payload: BoardData, username: str = Depends(require_username)) -> BoardData:
    db.save_board_for_user(username, payload)
    return payload


@app.get("/api/chat/history", response_model=list[ChatMessage])
def chat_history(username: str = Depends(require_username)) -> list[ChatMessage]:
    return db.get_chat_history(username)


@app.post("/api/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, username: str = Depends(require_username)) -> ChatResponse:
    board = db.get_board_for_user(username)
    history = db.get_chat_history(username)
    try:
        result = openrouter.ask_ai(board=board, history=history, user_message=payload.message)
    except openrouter.AIProviderError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(error),
        ) from error
    except (httpx.HTTPError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI request failed: {error}",
        ) from error

    db.add_chat_message(username, ChatMessage(role="user", content=payload.message))
    db.add_chat_message(username, ChatMessage(role="assistant", content=result.assistant_reply))
    board_updated = result.updated_board is not None
    if board_updated:
        db.save_board_for_user(username, result.updated_board)
    return ChatResponse(
        message=result.assistant_reply,
        board_updated=board_updated,
        board=result.updated_board if board_updated else None,
    )


@app.get("/api/ai/ping")
def ai_ping(username: str = Depends(require_username)) -> dict[str, str]:
    _ = username
    try:
        answer = openrouter.ping_ai()
    except openrouter.AIProviderError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(error),
        ) from error
    except httpx.HTTPError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI ping failed: {error}",
        ) from error
    return {"answer": answer}


def _serve_index() -> FileResponse:
    index_path = FRONTEND_DIST / "index.html"
    if not index_path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"Frontend build not found at {FRONTEND_DIST}. "
                "Run frontend build or use Docker image build."
            ),
        )
    return FileResponse(index_path)


if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
else:

    @app.get("/{path:path}")
    def fallback(path: str) -> FileResponse:
        _ = path
        return _serve_index()
