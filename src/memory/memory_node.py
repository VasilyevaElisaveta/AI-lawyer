from typing import Any

from langchain_core.messages import BaseMessage, HumanMessage, RemoveMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.message import REMOVE_ALL_MESSAGES

from .config import KEEP_RECENT_MESSAGES, MAX_MESSAGES_WITHOUT_SUMMARY
from .summarizer import summarize_messages


def _split_for_summary(
    messages: list[BaseMessage],
) -> tuple[list[BaseMessage], list[BaseMessage], str | None]:
    previous_summary = None
    if messages and isinstance(messages[0], SystemMessage):
        previous_summary = str(messages[0].content or "")

    if KEEP_RECENT_MESSAGES <= 0:
        old = list(messages)
        recent: list[BaseMessage] = []
    else:
        recent = messages[-KEEP_RECENT_MESSAGES:]
        old = messages[:-KEEP_RECENT_MESSAGES]

    if old and isinstance(old[0], SystemMessage):
        old = old[1:]

    return old, recent, previous_summary


async def memory_node(
    state: dict[str, Any],
    llm,
    config: RunnableConfig | None = None,
) -> dict[str, Any]:
    messages: list[BaseMessage] = list(state.get("messages") or [])
    raw_input = (state.get("raw_input") or "").strip()

    new_human: HumanMessage | None = None
    if raw_input:
        last_content = getattr(messages[-1], "content", None) if messages else None
        if last_content != raw_input:
            new_human = HumanMessage(content=raw_input)
            messages.append(new_human)

    if len(messages) <= MAX_MESSAGES_WITHOUT_SUMMARY:
        if new_human:
            return {"messages": [new_human]}
        return {}

    old_messages, recent, summary_from_system = _split_for_summary(messages)
    previous_summary = state.get("conversation_summary") or summary_from_system

    summary, metadata = await summarize_messages(
        state,
        old_messages,
        llm,
        previous_summary,
        config=config,
    )

    summary_message = SystemMessage(
        content=f"Сводка предыдущей беседы:\n{summary}",
    )

    compacted: list[BaseMessage] = [summary_message, *recent]
    if KEEP_RECENT_MESSAGES <= 0 and new_human is not None:
        compacted.append(new_human)

    return {
        "messages": [
            RemoveMessage(id=REMOVE_ALL_MESSAGES),
            *compacted,
        ],
        "conversation_summary": summary,
        "usage_metadata": metadata,
    }
