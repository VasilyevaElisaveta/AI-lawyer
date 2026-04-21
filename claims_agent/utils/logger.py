"""Настройка логирования для всего приложения."""
from __future__ import annotations

import logging
import sys


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    # уровень задаётся через config, но здесь — безопасный импорт
    try:
        from claims_agent.config import get_settings
        logger.setLevel(get_settings().log_level)
    except Exception:
        logger.setLevel(logging.INFO)

    return logger