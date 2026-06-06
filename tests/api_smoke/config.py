import os
from pathlib import Path

from dotenv import load_dotenv


SMOKE_DIR = Path(__file__).resolve().parent
TESTS_DIR = SMOKE_DIR.parent
ENV_FILE = TESTS_DIR / ".env"
LOG_FILE = SMOKE_DIR / "logs.txt"

load_dotenv(ENV_FILE, override=True)

BASE_URL = os.getenv("INFERENCE_BASE_URL", "http://localhost:8000").rstrip("/")
API_PREFIX = os.getenv("INFERENCE_API_PREFIX", "/api/chat").rstrip("/")
HTTP_TIMEOUT = float(os.getenv("SMOKE_HTTP_TIMEOUT", "600"))


def api_url(path: str) -> str:
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{BASE_URL}{API_PREFIX}{path}"
