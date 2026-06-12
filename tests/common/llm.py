"""Фабрика LLM + единый сборщик токенов для тестов."""
import os
from contextlib import contextmanager
from typing import Any, Iterator

from langchain_core.callbacks import UsageMetadataCallbackHandler

from . import bootstrap  # noqa: F401  (важно для sys.path)
from agents.llm_client import DEFAULT_GIGACHAT_PARAMS, create_gigachat


def build_llm(max_tokens: int = 1024, temperature: float = 0.0):
    """GigaChat с фиксированной температурой для воспроизводимости."""
    gigachat_params = {
        **DEFAULT_GIGACHAT_PARAMS,
        "max_tokens": max_tokens,
        "streaming": False,
    }
    return create_gigachat(
        os.getenv("LLM_MODEL", "GigaChat"),
        credentials=os.getenv("SBER_AUTH", ""),
        scope=os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS"),
        temperature=temperature,
        **gigachat_params,
    )


@contextmanager
def usage_capture(llm) -> Iterator[tuple[Any, dict]]:
    """
    Возвращает (tracked_llm, usage). Все LLM-вызовы через `tracked_llm`
    в блоке обновляют `usage`-словарь токенами из `response.usage_metadata`.

    Пример:
        with usage_capture(llm) as (tracked_llm, usage):
            node(state, tracked_llm, config=None)
        # usage = {"input_tokens": int, "output_tokens": int, "total_tokens": int}
    """
    handler = UsageMetadataCallbackHandler()
    tracked = llm.with_config(callbacks=[handler])
    usage: dict[str, int] = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    try:
        yield tracked, usage
    finally:
        for model_usage in handler.usage_metadata.values():
            for key in usage:
                usage[key] += int(model_usage.get(key, 0) or 0)
