import os

from langchain_gigachat import GigaChat
from langchain_core.messages import BaseMessage
from dotenv import load_dotenv

load_dotenv()

SBER_AUTH = os.getenv("SBER_AUTH")

class GigaChatClient:
    def __init__(
        self,
        model: str = "GigaChat-2-Max",
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

    async def ainvoke(self, messages: list[BaseMessage]) -> str:
        response = await self.client.ainvoke(messages)
        return getattr(response, "content", str(response))