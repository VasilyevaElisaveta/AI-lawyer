"""
Подготовка окружения для тестов: путь до src, переменные окружения из tests/.env.
Импортировать первым в run_test.py.
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[2]
TESTS_DIR = REPO_ROOT / "tests"
SRC_DIR = REPO_ROOT / "src"
LOGGER_SRC = REPO_ROOT / "libs" / "logger" / "src"


def setup() -> Path:
    """Добавляет src в sys.path и грузит tests/.env. Возвращает корень репозитория."""
    for path in (SRC_DIR, LOGGER_SRC):
        path_str = str(path)
        if path.exists() and path_str not in sys.path:
            sys.path.insert(0, path_str)

    env_file = TESTS_DIR / ".env"
    if env_file.exists():
        load_dotenv(env_file, override=False)

    os.environ.setdefault("LOGS_DIR", "")
    os.environ.setdefault("MODE", "DEBUG")

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8")
            except (TypeError, ValueError):
                pass

    return REPO_ROOT


setup()
