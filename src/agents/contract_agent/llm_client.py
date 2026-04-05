from __future__ import annotations

import asyncio
import os
from typing import Any

from langchain_gigachat import GigaChat
from langchain_core.messages import BaseMessage
from dotenv import load_dotenv

load_dotenv()

SBER_AUTH = os.getenv("SBER_AUTH")

class GigaChatClient:
    def __init__(
        self,
        model: str = "GigaChat",
        temperature: float = 0.0,
    ) -> None:
        credentials = SBER_AUTH or os.getenv("SBER_AUTH")
        if not credentials:
            raise RuntimeError("Environment variable SBER_AUTH is required for GigaChatClient")

        self.client = GigaChat(
            credentials=credentials,
            model=model,
            profanity_check=False,
            verify_ssl_certs=False,
            temperature=temperature,
            top_p=0.1,
            max_tokens=128,
            timeout=120,
        )

    async def invoke(self, messages: list[BaseMessage]) -> str:
        response = await asyncio.to_thread(self.client.invoke, messages)
        return getattr(response, "content", str(response))

    async def complete(self, system: str, prompt: str) -> str:
        return await self.invoke(
            [
                BaseMessage.parse_obj({"type": "system", "text": system}),
                BaseMessage.parse_obj({"type": "human", "text": prompt}),
            ]
        )
