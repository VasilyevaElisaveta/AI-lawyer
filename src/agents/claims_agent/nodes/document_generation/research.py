"""
Модуль правового исследования.
Прототип: генерация применимых норм через LLM.
Будущее: RAG по векторной БД с кодексами и законами.
"""
import os
from typing import Any

from logger import LoggerFactory

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from ...state import ClaimsAgentState
from ...prompts import (
    RESEARCH_HUMAN,
    RESEARCH_SYSTEM,
    render_template
)


logger = LoggerFactory.get_logger(
    name=__name__,
    logs_path=os.getenv("LOGS_DIR"),
    log_file=os.getenv("LOGS_FILE") if os.getenv("MODE") != "DEBUG" else None,
)

_CASE_TYPE_LABELS = {
    "civil": "Гражданское судопроизводство (суд общей юрисдикции)",
    "arbitration": "Арбитражное судопроизводство",
}


def research_node(
        state: ClaimsAgentState,
        llm,
        config: RunnableConfig,
    ) -> dict[str, Any]:
    """Узел графа: определение применимых норм права."""
    logger.info("Research node started")

    case_type = state.get("case_type", "civil")

    prompt = render_template(
        RESEARCH_HUMAN,
        {
            "case_type_label": _CASE_TYPE_LABELS.get(case_type, case_type),
            "case_category": state.get("case_category", "other"),
            "is_property_dispute": state.get("is_property_dispute", False),
            "facts": state.get("facts", ""),
            "claims": state.get("claims", ""),
        },
    )

    try:
        response = llm.invoke(
            [
                SystemMessage(content=RESEARCH_SYSTEM),
                HumanMessage(content=prompt),
            ],
            config=config,
        )
        content = response.content
        data = _parse_research(content)
        logger.info("  Research completed, laws length: %d chars", len(data.get("applicable_laws", "")))
        return data

    except Exception as e:
        logger.error("Research failed: %s", e)
        return {
            "applicable_laws": "[Не удалось определить применимые нормы — требуется ручная проверка]",
            "legal_positions": "",
        }


def _parse_research(text: str) -> dict[str, Any]:
    import re
    import json

    # Извлечение JSON из markdown-блока
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if m:
        raw = m.group(1)
    else:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            raw = text[start: end + 1]
        else:
            # Если JSON не найден — весь текст как applicable_laws
            return {"applicable_laws": text.strip(), "legal_positions": ""}

    try:
        # Попытка парсинга
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.warning("JSON decode error: %s. Trying to clean...", e)

        # Очистка от управляющих символов
        import unicodedata

        # Удаляем все управляющие символы, кроме \n и \t
        cleaned = ''.join(
            ch for ch in raw
            if ch in ['\n', '\t'] or unicodedata.category(ch)[0] != 'C'
        )

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            # Последняя попытка: берём текст как есть
            logger.error("Failed to parse JSON even after cleaning. Using raw text.")
            return {
                "applicable_laws": "[Ошибка парсинга норм права. Требуется ручная проверка]\n\n" + text[:500],
                "legal_positions": ""
            }

    return {
        "applicable_laws": data.get("applicable_laws", ""),
        "legal_positions": data.get("legal_positions", ""),
    }


# ═══════════════════════════════════════════════════════════════
#  Заготовка для RAG
# ═══════════════════════════════════════════════════════════════

def _rag_search(query: str, top_k: int = 5) -> list[str]:
    """
    TODO: Поиск по векторной БД с кодексами/законами.
    Будет вызываться из research_node вместо/дополнительно к LLM.
    """
    # from claims_agent.services.vector_db import get_retriever
    # retriever = get_retriever()
    # docs = retriever.invoke(query)
    # return [d.page_content for d in docs[:top_k]]
    return []