from __future__ import annotations

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from src.agents.llm_client import GigaChatClient


async def summarize_messages(
    messages,
    llm: GigaChatClient,
    previous_summary: str | None = None,
    config: RunnableConfig | None = None
) -> str:

    dialog_text = "\n".join(
        [f"{msg.type}: {msg.content}" for msg in messages]
    )

    content = f"""
    Ты обновляешь долговременную память диалога.
    Верни результат строго в формате:

    ФАКТЫ:
    ...

    РЕШЕНИЯ:
    ...

    ДОГОВОРЁННОСТИ:
    ...

    ПАРАМЕТРЫ:
    ...

    КОНТЕКСТ:
    ...

    ---

    СТАРАЯ ПАМЯТЬ:
    {previous_summary}

    НОВЫЕ СООБЩЕНИЯ:
    {dialog_text}

    ---

    Правила:
    - не теряй важные факты
    - не дублируй
    - обновляй значения при изменениях
    - убирай устаревшее
    """

    prompt = HumanMessage(content=content)
    summary = await llm.ainvoke([prompt], config=config)

    return summary