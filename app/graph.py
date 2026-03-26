"""
Оркестратор: сборка LangGraph-графа из модулей.

Единый граф для обоих типов документов (lawsuit / pretrial_claim).
Тип документа определяется полем doc_type в state и роутится внутри узлов.
"""
from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from app.core.config import get_settings
from app.core.state import AgentState
from app.modules import (
    calculator_node,
    classification_node,
    generator_node,
    intake_node,
    qa_node,
    research_node,
    validation_node,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════
#  Финализирующий узел
# ═══════════════════════════════════════════════════════════════

def finalize_node(state: AgentState) -> dict[str, Any]:
    """Копирует generated_document → final_document."""
    logger.info("▶ Finalize node")
    return {"final_document": state.get("generated_document", "")}


# ═══════════════════════════════════════════════════════════════
#  Условные маршруты (edges)
# ═══════════════════════════════════════════════════════════════

def _route_after_validation(state: AgentState) -> str:
    """
    После валидации:
      • valid           → research
      • invalid + retry → intake   (только если есть raw_input)
      • invalid + done  → research (идём с тем что есть)
    """
    if state.get("is_valid", False):
        return "research"

    settings = get_settings()
    attempts = state.get("validation_attempts", 0)
    has_raw_input = bool(state.get("raw_input"))

    if has_raw_input and attempts < settings.max_validation_retries:
        logger.info("  Routing back to intake for re-extraction (attempt %d)", attempts)
        return "intake"

    logger.info("  Validation incomplete but proceeding to research")
    return "research"


def _route_after_qa(state: AgentState) -> str:
    """
    После QA:
      • passed         → finalize
      • failed + retry → generator
      • failed + done  → finalize (отдаём лучшее что есть)
    """
    if state.get("qa_passed", False):
        return "finalize"

    settings = get_settings()
    attempts = state.get("qa_attempts", 0)

    if attempts < settings.max_qa_retries:
        logger.info("  Routing back to generator for rework (attempt %d)", attempts)
        return "generator"

    logger.info("  QA retries exhausted — finalizing as-is")
    return "finalize"


# ═══════════════════════════════════════════════════════════════
#  Сборка графа
# ═══════════════════════════════════════════════════════════════

def create_graph() -> Any:
    """
    Создаёт и компилирует LangGraph StateGraph.
    Возвращает скомпилированный граф, готовый к .invoke() / .stream().

    Единый граф для обоих типов документов.
    Тип определяется через state["doc_type"]:
      • "lawsuit"        — исковое заявление (по умолчанию)
      • "pretrial_claim" — досудебная претензия
    """
    builder = StateGraph(AgentState)

    # ── Узлы ──────────────────────────────────────────────────
    builder.add_node("intake", intake_node)
    builder.add_node("classification", classification_node)
    builder.add_node("validation", validation_node)
    builder.add_node("research", research_node)
    builder.add_node("calculator", calculator_node)
    builder.add_node("generator", generator_node)
    builder.add_node("qa", qa_node)
    builder.add_node("finalize", finalize_node)

    # ── Рёбра ─────────────────────────────────────────────────
    builder.set_entry_point("intake")

    builder.add_edge("intake", "classification")
    builder.add_edge("classification", "validation")

    # Условный переход после валидации
    builder.add_conditional_edges(
        "validation",
        _route_after_validation,
        {
            "research": "research",
            "intake": "intake",
        },
    )

    builder.add_edge("research", "calculator")
    builder.add_edge("calculator", "generator")
    builder.add_edge("generator", "qa")

    # Условный переход после QA
    builder.add_conditional_edges(
        "qa",
        _route_after_qa,
        {
            "finalize": "finalize",
            "generator": "generator",
        },
    )

    builder.add_edge("finalize", END)

    # ── Компиляция ────────────────────────────────────────────
    graph = builder.compile()
    logger.info("LangGraph compiled successfully")
    return graph