from typing import Any

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from .config import SUMMARY_TRIGGER_TOKENS, KEEP_LAST_MESSAGES
from .token_counter import TokenCounter
from .summarizer import summarize_messages

from ..agents.llm_client import GigaChatClient


async def memory_node(
    state: dict[str, Any],
    llm: GigaChatClient,
    config: RunnableConfig | None = None
) -> dict[str, Any]:
    """Сокращает историю сообщений и создаёт сводку при переполнении контекста."""
    messages: list[BaseMessage] = state.get("messages") or []

    raw_input = state.get("raw_input", "")
    if raw_input:
        if not messages or getattr(messages[-1], "content", None) != raw_input:
            messages.append(HumanMessage(content=raw_input))

    state["messages"] = messages

    if not messages:
        return dict(state)

    counter = TokenCounter(llm)
    tokens = counter.count_messages_tokens(messages)
    state["total_tokens"] = tokens

    if tokens < SUMMARY_TRIGGER_TOKENS:
        return dict(state)

    if len(messages) <= KEEP_LAST_MESSAGES:
        return dict(state)

    old_messages = messages[:-KEEP_LAST_MESSAGES]

    previous_summary = state.get("conversation_summary")

    summary = await summarize_messages(
        old_messages,
        llm,
        previous_summary,
        config=config
    )

    state["conversation_summary"] = summary

    new_messages = messages[-KEEP_LAST_MESSAGES:]
    summary_message = SystemMessage(content=f"Сводка предыдущей беседы:\n{summary}")
    state["messages"] = [summary_message, *new_messages]

    return dict(state)
