from collections.abc import AsyncIterator
from typing import Any
import httpx


class AgentClient:
    def __init__(self, base_url: str, chat_path: str, timeout_seconds: float) -> None:
        self._base_url = base_url.rstrip("/")
        self._chat_path = chat_path if chat_path.startswith("/") else f"/{chat_path}"
        self._timeout = timeout_seconds

    @property
    def url(self) -> str:
        return f"{self._base_url}{self._chat_path}"

    async def send_message(self, *, message: str, conversation_id: str | None = None) -> str:
        payload: dict[str, Any] = {"message": message}
        if conversation_id is not None:
            payload["conversation_id"] = conversation_id

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(self.url, json=payload)
            response.raise_for_status()

            try:
                data = response.json()
            except ValueError:
                text = response.text.strip()
                if text:
                    return text
                raise ValueError("Agent returned empty response")

        return self._extract_reply(data)

    async def stream_message(self, *, message: str, conversation_id: str | None = None) -> AsyncIterator[str]:
        """
        Будущий потоковый режим.
        Сейчас не используется в API, но контракт уже есть.
        """
        raise NotImplementedError("Streaming mode is not enabled yet")

    @staticmethod
    def _extract_reply(data: Any) -> str:
        if isinstance(data, str):
            text = data.strip()
            if text:
                return text

        if isinstance(data, dict):
            for key in ("reply", "message", "content", "text", "answer"):
                value = data.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()

            choices = data.get("choices")
            if isinstance(choices, list) and choices:
                first = choices[0]
                if isinstance(first, dict):
                    for key in ("message", "delta", "content", "text"):
                        value = first.get(key)
                        if isinstance(value, str) and value.strip():
                            return value.strip()
                        if isinstance(value, dict):
                            nested = value.get("content") or value.get("text")
                            if isinstance(nested, str) and nested.strip():
                                return nested.strip()

        raise ValueError(f"Cannot extract agent reply from response: {data!r}")