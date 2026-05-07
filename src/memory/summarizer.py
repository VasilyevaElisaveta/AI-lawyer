from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from agents.utils import update_tokens_metadata


async def summarize_messages(
    state,
    messages,
    llm,
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
    response = await llm.ainvoke([prompt], config=config)
    summary = response.content
    usage_metadata = getattr(response, "usage_metadata", None) or {}
    previous_usage_metadata = state.get("usage_metadata", {})
    usage_metadata = update_tokens_metadata(
        previous_usage_metadata, 
        usage_metadata, 
        ["input_tokens", "output_tokens", "total_tokens"]
    )
    return summary, usage_metadata