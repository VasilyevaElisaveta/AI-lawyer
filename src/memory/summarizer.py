from __future__ import annotations

from langchain_core.messages import HumanMessage

from app.services.llm_client import GigaChatClient


async def summarize_messages(
    messages,
    llm: GigaChatClient,
) -> str:

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

{messages}
"""
    )

    summary = await llm.invoke(
        [prompt]
    )

    return summary