from __future__ import annotations

from langchain_core.messages import BaseMessage

from src.agents.llm_client import GigaChatClient


class TokenCounter:

    def __init__(self, llm: GigaChatClient):
        self.llm = llm

    def count_messages_tokens(
        self,
        messages: list[BaseMessage],
    ) -> int:

        return self.llm.client.get_num_tokens_from_messages(
            messages
        )