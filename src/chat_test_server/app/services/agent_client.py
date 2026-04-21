from collections.abc import AsyncIterator
from uuid import uuid4
import httpx
import logging
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class InferenceResponse(BaseModel):
    reply: str
    handled_by_agent: bool = True
    document_created: bool = False


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
        payload = {
            "raw_input": message,
            "thread_id": conversation_id or str(uuid4()),
            "agent_type": None,
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(self.url, json=payload)
            if response.status_code >= 400:
                logger.error("HTTP %s from %s", response.status_code, self.url)
                logger.error("Request payload: %s", payload)
                logger.error("Response body: %s", response.text)

            response.raise_for_status()

            response_data = response.json()
            return InferenceResponse(
                reply=response_data.get("reply", ""),
                handled_by_agent=response_data.get("handled_by_agent", True),
                document_created=response_data.get("document_created", False),
            )

    async def stream_message(
        self,
        *,
        message: str,
        conversation_id: str | None = None
    ) -> AsyncIterator[str]:
        raise NotImplementedError