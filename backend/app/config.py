from pathlib import Path
import os


MODEL_NAME = "google/gemma-4-26b-a4b-it:free"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

BASE_DIR = Path(__file__).resolve().parents[2]
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", str(BASE_DIR / "data" / "pm.db")))
FRONTEND_DIST = Path(os.getenv("FRONTEND_DIST", str(BASE_DIR / "frontend" / "out")))

DEFAULT_USERNAME = "user"
DEFAULT_PASSWORD = "password"
