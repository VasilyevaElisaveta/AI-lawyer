from __future__ import annotations

from typing import Any

from langchain_core.messages import BaseMessage

from .config import (
    SUMMARY_TRIGGER_TOKENS,
    KEEP_LAST_MESSAGES,
)

from .token_counter import TokenCounter
from .summarizer import summarize_messages

from src.agents.contract_agent.state import AgentState
from src.agents.llm_client import GigaChatClient


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

    state["total_tokens"] = tokens

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

    state["total_tokens"] = tokens

    new_messages = messages[
        -KEEP_LAST_MESSAGES:
    ]

    return {
        "messages": new_messages,
    }