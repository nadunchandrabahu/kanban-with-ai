from pathlib import Path
import os

MODEL_NAME = "gemini-3.5-flash-lite"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

BASE_DIR = Path(__file__).resolve().parents[2]
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", str(BASE_DIR / "data" / "pm.db")))
FRONTEND_DIST = Path(os.getenv("FRONTEND_DIST", str(BASE_DIR / "frontend" / "out")))

DEFAULT_USERNAME = "user"
DEFAULT_PASSWORD = "password"
