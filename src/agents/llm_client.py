import inspect
import os
from dotenv import load_dotenv

from langchain_gigachat import GigaChat


load_dotenv()

DEFAULT_GIGACHAT_PARAMS = {
    "profanity_check": False,
    "verify_ssl_certs": False,
    "top_p": 0.1,
    "max_tokens": 128,
    "timeout": 120,
    "streaming": True,
}


def create_gigachat(
    model: str,
    temperature: float | None = None,
    config=None,
    **kwargs,
) -> GigaChat:
    params = {
        "model": model or os.getenv("LLM_MODEL", "GigaChat"),
        **kwargs,
    }

    if temperature is not None:
        params["temperature"] = temperature

    allowed = set(inspect.signature(GigaChat).parameters)
    unknown = set(params) - allowed
    if unknown:
        raise TypeError(f"Unsupported GigaChat arguments: {sorted(unknown)}")

    llm = GigaChat(**params)
    if config is not None:
        llm = llm.with_config(**config)
    return llm