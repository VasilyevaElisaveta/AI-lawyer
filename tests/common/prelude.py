"""
Подключение корня репозитория в sys.path. Использовать в начале скриптов:

    from pathlib import Path
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from tests.common.prelude import *  # noqa: F401, F403

После этого доступны bootstrap (sys.path для src), build_llm, usage_capture и IO-утилиты.
"""
from . import bootstrap
from .io_utils import (
    parse_json_column,
    read_jsonl,
    read_results_csv,
    write_json,
    write_jsonl,
    write_results_csv,
)
from .llm import build_llm, usage_capture

__all__ = [
    "bootstrap",
    "build_llm",
    "usage_capture",
    "parse_json_column",
    "read_jsonl",
    "read_results_csv",
    "write_json",
    "write_jsonl",
    "write_results_csv",
]
