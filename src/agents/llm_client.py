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
}


def create_gigachat(
    model: str,
    temperature: float | None = None,
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

    return GigaChat(**params)