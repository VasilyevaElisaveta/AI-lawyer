from __future__ import annotations

from langchain_core.messages import HumanMessage

from src.agents.llm_client import GigaChatClient


async def summarize_messages(
    messages,
    llm: GigaChatClient,
) -> str:

    # Преобразуем сообщения в строку для промпта
    dialog_text = "\n".join([f"{msg.type}: {msg.content}" for msg in messages])

    prompt = HumanMessage(
        content=f"""
Суммаризируй диалог.

Сохрани:

- факты
- даты
- суммы
- обязательства
- юридические детали

Диалог:

{dialog_text}
"""
    )

    summary = await llm.ainvoke(
        [prompt]
    )

    return summary