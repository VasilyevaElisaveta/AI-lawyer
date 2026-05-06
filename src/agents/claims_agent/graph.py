"""
Агент для генерации исковых заявлений и претензий.
"""
from __future__ import annotations

import asyncio
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, END

from .state import ClaimsAgentState
from .nodes import (
    intake_node,
    classification_node,
    validation_node,
    research_node,
    calculator_node,
    generator_node,
    qa_node,
)
from .utils.logger import get_logger
from .utils.docx_generator import generate_docx_base64

logger = get_logger(__name__)

# Допустимые типы документов
_DOCUMENT_TYPES = {"lawsuit", "complaint"}
_DEFAULT_DOCUMENT_TYPE = "lawsuit"


class ClaimsAgent:
    """
    Агент для генерации юридических документов: исков и досудебных претензий.
    """

    def __init__(self):
        self.graph = self._build_graph()
        logger.info("ClaimsAgent initialized")

    def _build_graph(self) -> Any:
        """Строит граф обработки."""
        builder = StateGraph(ClaimsAgentState)

        # Узлы
        builder.add_node("intake", intake_node)
        builder.add_node("classification", classification_node)
        builder.add_node("validation", validation_node)
        builder.add_node("research", research_node)
        builder.add_node("calculator", calculator_node)
        builder.add_node("generator", generator_node)
        builder.add_node("qa", qa_node)
        builder.add_node("finalize", self._finalize_node)

        # Рёбра
        builder.set_entry_point("intake")
        builder.add_edge("intake", "classification")
        builder.add_edge("classification", "validation")

        # Условная маршрутизация после валидации
        builder.add_conditional_edges(
            "validation",
            self._route_after_validation,
            {"research": "research", "intake": "intake"},
        )

        builder.add_edge("research", "calculator")
        builder.add_edge("calculator", "generator")
        builder.add_edge("generator", "qa")

        # Условная маршрутизация после QA
        builder.add_conditional_edges(
            "qa",
            self._route_after_qa,
            {"finalize": "finalize", "generator": "generator"},
        )

        builder.add_edge("finalize", END)

        memory = MemorySaver()
        return builder.compile(checkpointer=memory)

    def _route_after_validation(self, state: ClaimsAgentState) -> str:
        """Маршрутизация после валидации."""
        if state.get("is_valid", False):
            return "research"

        attempts = state.get("validation_attempts", 0)
        has_raw = bool(state.get("raw_input"))

        if has_raw and attempts < 2:
            logger.info("Validation failed, retrying intake (attempt %d)", attempts)
            return "intake"

        logger.warning("Validation failed but proceeding to research")
        return "research"

    def _route_after_qa(self, state: ClaimsAgentState) -> str:
        """Маршрутизация после QA."""
        if state.get("qa_passed", False):
            return "finalize"

        attempts = state.get("qa_attempts", 0)
        if attempts < 2:
            logger.info("QA failed, regenerating (attempt %d)", attempts)
            return "generator"

        logger.warning("QA retries exhausted, finalizing")
        return "finalize"

    def _finalize_node(self, state: ClaimsAgentState) -> dict[str, Any]:
        """Финализация: генерация DOCX в base64."""
        logger.info("Finalize node started")

        document_text = state.get("generated_document", "")
        document_type = state.get("document_type", _DEFAULT_DOCUMENT_TYPE)

        if not document_text:
            return {
                "final_document": "",
                "document_base64": "",
                "pipeline_status": "failed",
                "error": "Документ не был сгенерирован",
            }

        try:
            docx_title = (
                "Досудебная претензия" if document_type == "complaint"
                else "Исковое заявление"
            )
            docx_base64 = generate_docx_base64(
                document_text,
                metadata={
                    "title": docx_title,
                    "plaintiff": state.get("plaintiff_info", ""),
                    "defendant": state.get("defendant_info", ""),
                    "court": state.get("court_info", ""),
                },
            )

            logger.info("DOCX generated, base64 length: %d", len(docx_base64))

            return {
                "final_document": document_text,
                "document_base64": docx_base64,
                "pipeline_status": "completed",
            }

        except Exception as e:
            logger.error("DOCX generation failed: %s", e, exc_info=True)
            return {
                "final_document": document_text,
                "document_base64": "",
                "pipeline_status": "completed_with_errors",
                "error": f"Ошибка генерации DOCX: {str(e)}",
            }

    async def process_user_message(
        self,
        user_message: str,
        thread_id: str,
        document_type: str = _DEFAULT_DOCUMENT_TYPE,
    ) -> dict[str, Any]:
        """
        Обработка сообщения пользователя.

        Args:
            user_message: Текст от пользователя (свободная форма или JSON)
            thread_id: ID диалога (для сохранения состояния между запросами)
            document_type: Тип документа — "lawsuit" (иск) или "complaint" (претензия).
                           Можно также передать внутри JSON-тела как поле "document_type".

        Returns:
            {
                "reply": str | dict,           # Текст ответа или base64 документа
                "handled_by_agent": "lawsuit",
                "document_created": bool
            }
        """
        logger.info(
            "Processing message for thread %s (document_type=%s)",
            thread_id,
            document_type,
        )

        try:
            import json as _json
            try:
                input_data = _json.loads(user_message)
                # Тип документа может быть задан внутри JSON-тела
                if "document_type" in input_data:
                    document_type = input_data["document_type"]
                initial_state: dict[str, Any] = {"input_data": input_data}
            except _json.JSONDecodeError:
                initial_state = {"raw_input": user_message}

            # Нормализация и проверка типа документа
            if document_type not in _DOCUMENT_TYPES:
                logger.warning(
                    "Unknown document_type '%s', falling back to '%s'",
                    document_type,
                    _DEFAULT_DOCUMENT_TYPE,
                )
                document_type = _DEFAULT_DOCUMENT_TYPE

            initial_state["document_type"] = document_type
            initial_state["request_id"] = thread_id
            initial_state["user_id"] = thread_id

            config = {"configurable": {"thread_id": thread_id}}

            final_state = await asyncio.to_thread(
                self.graph.invoke,
                initial_state,
                config,
            )

            return self._format_response(final_state)

        except Exception as e:
            logger.error("Processing failed: %s", e, exc_info=True)
            return {
                "reply": f"Произошла ошибка при обработке запроса: {str(e)}",
                "handled_by_agent": "lawsuit",
                "document_created": False,
                "error": str(e),
            }

    def _format_response(self, state: ClaimsAgentState) -> dict[str, Any]:
        """Форматирование финального ответа."""
        pipeline_status = state.get("pipeline_status", "unknown")
        error = state.get("error", "")
        document_type = state.get("document_type", _DEFAULT_DOCUMENT_TYPE)

        document_base64 = state.get("document_base64", "")
        if document_base64:
            return {
                "reply": document_base64,
                "handled_by_agent": "lawsuit",
                "document_created": True,
                "document_type": document_type,
                "status": pipeline_status,
                "metadata": {
                    "plaintiff": state.get("plaintiff_info", "")[:100],
                    "defendant": state.get("defendant_info", "")[:100],
                    "total_claim": state.get("total_claim", 0),
                    "state_duty": state.get("state_duty", 0),
                },
            }

        if error:
            reply = f"Не удалось создать документ:\n{error}"
        elif not state.get("is_valid", True):
            errors = state.get("validation_errors", [])
            doc_label = "претензии" if document_type == "complaint" else "искового заявления"
            reply = (
                f"Недостаточно данных для создания {doc_label}:\n"
                + "\n".join(f"• {err}" for err in errors)
                + "\n\nПожалуйста, дополните информацию."
            )
        else:
            reply = "Обработка завершена, но документ не был сгенерирован."

        return {
            "reply": reply,
            "handled_by_agent": True,
            "document_created": False,
            "document_type": document_type,
            "status": pipeline_status,
        }
