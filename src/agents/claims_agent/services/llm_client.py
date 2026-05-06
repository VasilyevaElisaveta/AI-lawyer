"""
Инициализация и переиспользование GigaChat LLM.
"""
import os
import time
from functools import lru_cache

from libs.logger import LoggerFactory

from langchain_gigachat import GigaChat
from langchain_core.messages import BaseMessage

from claims_agent.config import get_settings


logger = LoggerFactory.get_logger(
    name=__name__,
    logs_path=os.getenv("LOGS_DIR"),
    log_file=os.getenv("LOGS_FILE") if os.getenv("MODE") is not "DEBUG" else None,
)


@lru_cache
def get_llm() -> GigaChat:
    """Синглтон-фабрика GigaChat."""
    s = get_settings()
    return GigaChat(
        credentials=s.gigachat_credentials,
        scope=s.gigachat_scope,
        model=s.gigachat_model,
        verify_ssl_certs=s.gigachat_verify_ssl,
        temperature=s.gigachat_temperature,
        max_tokens=s.gigachat_max_tokens,
        timeout=s.gigachat_timeout,
    )


def invoke_llm(
    messages: list[BaseMessage],
    *,
    max_retries: int = 2,
    backoff: float = 2.0,
) -> str:
    """
    Вызов LLM с повторными попытками.
    Возвращает content ответа (str).
    """
    llm = get_llm()
    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            response = llm.invoke(messages)
            content: str = response.content if hasattr(response, "content") else str(response)
            return content
        except Exception as exc:
            last_error = exc
            logger.warning(
                "LLM call failed (attempt %d/%d): %s",
                attempt,
                max_retries,
                exc,
            )
            if attempt < max_retries:
                time.sleep(backoff * attempt)

    raise RuntimeError(f"LLM call failed after {max_retries} attempts: {last_error}")