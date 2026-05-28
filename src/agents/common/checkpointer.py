"""
Фабрика checkpointer для LangGraph.

MODE=DEBUG  → MemorySaver (состояние в ОЗУ, сбрасывается при рестарте).
MODE!=DEBUG → AsyncRedisSaver (Redis Stack, RediSearch; только database 0).

Изоляция агентов в Redis: префикс в thread_id (claims:uuid, general_questions:uuid, …).
"""
import logging
import os
import re
from functools import lru_cache
from typing import Any

from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger(__name__)

_shared_redis_saver: Any | None = None


def is_debug_mode() -> bool:
    return (os.getenv("MODE") or "DEBUG").strip().upper() == "DEBUG"


def _running_in_docker() -> bool:
    return os.path.exists("/.dockerenv")


def _is_local_redis_host(url: str) -> bool:
    return bool(re.search(r"redis://(localhost|127\.0\.0\.1)(:|/|$)", url))


def _replace_redis_host(url: str, host: str) -> str:
    return re.sub(r"redis://(localhost|127\.0\.0\.1)", f"redis://{host}", url, count=1)


@lru_cache(maxsize=1)
def _redis_url() -> str:
    """RediSearch-индексы LangGraph работают только на database 0."""
    url = (os.getenv("REDIS_URL") or "redis://localhost:6379").strip()
    if _running_in_docker() and _is_local_redis_host(url):
        url = _replace_redis_host(url, "redis")
        logger.warning(
            "REDIS_URL указывал на localhost внутри контейнера — "
            "используем хост redis (%s)",
            url,
        )
    base = re.sub(r"/\d+$", "", url.rstrip("/"))
    return f"{base}/0"


def graph_checkpoint_config(agent_key: str, thread_id: str) -> dict[str, Any]:
    """
    configurable для LangGraph.

    В PROD thread_id в Redis получает префикс агента, чтобы графы не пересекались
    на одной database 0.
    """
    if is_debug_mode():
        storage_thread_id = thread_id
    else:
        storage_thread_id = f"{agent_key}:{thread_id}"
    return {"configurable": {"thread_id": storage_thread_id}}


def create_checkpointer(agent_key: str) -> Any:
    """
    Создаёт checkpointer для графа агента.

    agent_key: claims | general_questions | router | contract
    """
    if is_debug_mode():
        logger.info(
            "Checkpointer для %s: MemorySaver (MODE=DEBUG)",
            agent_key,
        )
        return MemorySaver()

    global _shared_redis_saver
    if _shared_redis_saver is None:
        from langgraph.checkpoint.redis.aio import AsyncRedisSaver

        url = _redis_url()
        logger.info("AsyncRedisSaver (общий для всех агентов): %s", url)
        _shared_redis_saver = AsyncRedisSaver(redis_url=url)

    return _shared_redis_saver


async def setup_checkpointer(checkpointer: Any) -> None:
    """Инициализирует индексы Redis Stack (no-op для MemorySaver)."""
    if is_debug_mode():
        return
    asetup = getattr(checkpointer, "asetup", None)
    if asetup is not None:
        await asetup()
        return
    setup = getattr(checkpointer, "setup", None)
    if setup is not None:
        setup()
