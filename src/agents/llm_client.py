import inspect

from langchain_gigachat import GigaChat


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
    *,
    credentials: str,
    scope: str = "GIGACHAT_API_PERS",
    temperature: float | None = None,
    config=None,
    **kwargs,
) -> GigaChat:
    """
    Фабрика GigaChat.

    credentials — ключ авторизации из личного кабинета GigaChat (SBER_AUTH).
    scope — версия API, привязанная к типу ключа (GIGACHAT_API_PERS / _B2B / _CORP).
    """
    params = {
        "model": model,
        "credentials": credentials,
        "scope": scope,
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
