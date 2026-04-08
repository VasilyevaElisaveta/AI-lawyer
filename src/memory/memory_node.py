from __future__ import annotations

from typing import Any

from langchain_core.messages import BaseMessage

from memory.config import (
    SUMMARY_TRIGGER_TOKENS,
    KEEP_LAST_MESSAGES,
)

from memory.token_counter import TokenCounter
from memory.summarizer import summarize_messages

from app.core.state import AgentState
from app.services.llm_client import GigaChatClient


async def memory_node(
    state: AgentState,
    llm: GigaChatClient,
) -> AgentState:

    messages: list[BaseMessage] = state.get(
        "messages",
        [],
    )

    if not messages:

        return state

    counter = TokenCounter(llm)

    tokens = counter.count_messages_tokens(
        messages
    )

    state.set(
        "total_tokens",
        tokens,
    )

    if tokens < SUMMARY_TRIGGER_TOKENS:

        return state

    old_messages = messages[
        :-KEEP_LAST_MESSAGES
    ]

    if not old_messages:

        return state

    summary = await summarize_messages(
        old_messages,
        llm,
    )

    previous_summary = state.get(
        "conversation_summary",
        "",
    )

    merged_summary = (
        previous_summary
        + "\n"
        + summary
    )

    state.set(
        "conversation_summary",
        merged_summary,
    )

    new_messages = messages[
        -KEEP_LAST_MESSAGES:
    ]

    state.set(
        "messages",
        new_messages,
    )

    return state