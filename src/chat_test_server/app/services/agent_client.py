from collections.abc import AsyncIterator
from typing import Any
import httpx
from pydantic import BaseModel


class InferenceResponse(BaseModel):
    reply_text: str
    document: str | None = None


class AgentClient:
    def __init__(self, base_url: str, chat_path: str, timeout_seconds: float) -> None:
        self._base_url = base_url.rstrip("/")
        self._chat_path = chat_path if chat_path.startswith("/") else f"/{chat_path}"
        self._timeout = timeout_seconds

    @property
    def url(self) -> str:
        return f"{self._base_url}{self._chat_path}"

    async def send_message(
        self,
        *,
        message: str,
        conversation_id: str | None = None
    ) -> InferenceResponse:

        payload: dict[str, Any] = {"message": message}
        if conversation_id:
            payload["conversation_id"] = conversation_id

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(self.url, json=payload)
            response.raise_for_status()

            data = response.json()

        return InferenceResponse.model_validate(data)

    async def stream_message(
        self,
        *,
        message: str,
        conversation_id: str | None = None
    ) -> AsyncIterator[str]:
        raise NotImplementedError