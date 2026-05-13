"""
Агент для генерации исковых заявлений и претензий.
"""
import os
import asyncio
from typing import Any
import hashlib

from logger import LoggerFactory

from langchain_core.tracers.context import collect_runs

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableConfig

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
from .utils.docx_generator import generate_docx_bytes, save_docx_file


logger = LoggerFactory.get_logger(
    name=__name__,
    logs_path=os.getenv("LOGS_DIR"),
    log_file=os.getenv("LOGS_FILE") if os.getenv("MODE") != "DEBUG" else None,
)

# Допустимые типы документов
_DOCUMENT_TYPES = {"lawsuit", "complaint"}
_DEFAULT_DOCUMENT_TYPE = "lawsuit"


class ClaimsAgent:
    """
    Агент для генерации юридических документов: исков и досудебных претензий.
    """

    def __init__(self, llm):
        self.llm = llm
        self.memory = MemorySaver()
        # В проде заменить на RedisSaver или другое долговременное хранилище.
        # from langgraph.checkpoint.redis import RedisSaver
        # self.memory = RedisSaver.from_conn_string(
        #     "redis://localhost:6379",
        #     key_prefix=f"contract_agent:"
        # )
        self.graph = self._build_graph(llm)
        logger.info("ClaimsAgent initialized")

    def _build_graph(self, llm) -> Any:
        """Строит граф обработки."""

        def intake_node_wrapper(state: ClaimsAgentState, config: RunnableConfig):
            return intake_node(state, llm, config)
        
        def classification_node_wrapper(state: ClaimsAgentState, config: RunnableConfig):
            return classification_node(state, llm, config)
        
        def validation_node_wrapper(state: ClaimsAgentState):
            return validation_node(state)
        
        def research_node_wrapper(state: ClaimsAgentState, config: RunnableConfig):
            return research_node(state, llm, config)
        
        def calculator_node_wrapper(state: ClaimsAgentState):
            return calculator_node(state)
        
        def generator_node_wrapper(state: ClaimsAgentState, config: RunnableConfig):
            return generator_node(state, llm, config)
        
        def qa_node_wrapper(state: ClaimsAgentState, config: RunnableConfig):
            return qa_node(state, llm, config)
        
        def _finalize_node_wrapper(state: ClaimsAgentState):
            return self._finalize_node(state)

        builder = StateGraph(ClaimsAgentState)

        # Узлы
        builder.add_node("intake", intake_node_wrapper)
        builder.add_node("classification", classification_node_wrapper)
        builder.add_node("validation", validation_node_wrapper)
        builder.add_node("research", research_node_wrapper)
        builder.add_node("calculator", calculator_node_wrapper)
        builder.add_node("generator", generator_node_wrapper)
        builder.add_node("qa", qa_node_wrapper)
        builder.add_node("finalize", _finalize_node_wrapper)

        # Рёбра
        builder.set_entry_point("intake")
        builder.add_edge("intake", "classification")
        builder.add_edge("classification", "validation")

        # Условная маршрутизация после валидации
        builder.add_conditional_edges(
            "validation",
            self._route_after_validation,
            {"research": "research", "intake": "intake", END: END},
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

        return builder.compile(checkpointer=self.memory)

    def _route_after_validation(self, state: ClaimsAgentState) -> str:
        """Маршрутизация после валидации."""
        if state.get("is_valid", False):
            return "research"

        attempts = state.get("validation_attempts", 0)
        has_raw = bool(state.get("raw_input"))

        if has_raw and attempts < 2:
            logger.info("Validation failed, retrying intake (attempt %d)", attempts)
            return "intake"

        logger.warning(
            "Validation failed after %d attempt(s), stopping pipeline. Errors: %s",
            attempts,
            state.get("validation_errors", []),
        )
        return END

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
                "document_path": "",
                "pipeline_status": "failed",
                "error": "Документ не был сгенерирован",
            }

        try:
            docx_title = (
                "Досудебная претензия" if document_type == "complaint"
                else "Исковое заявление"
            )
            docx_bytes = generate_docx_bytes(
                document_text,
                metadata={
                    "title": docx_title,
                    "plaintiff": state.get("plaintiff_info", ""),
                    "defendant": state.get("defendant_info", ""),
                    "court": state.get("court_info", ""),
                },
            )
            h = hashlib.blake2b(docx_bytes, digest_size=int(os.getenv("HASH_LENGTH"))).hexdigest()

            logger.info(f"DOCX generated, bytes length: {len(docx_bytes)}, hash: {h}")

            docx_directory = (
                f"{os.getenv('GENERATED_DOCX_PATH')}/"
                f"{state.get('user_metadata', {}).get('user_id', 'unknown_user')}/"
                f"{state.get('user_metadata', {}).get('thread_id', 'unknown_thread')}"
            )
            os.makedirs(docx_directory, exist_ok=True)
            docx_file = f"{docx_directory}/{h}.docx"
            i = 1
            while os.path.exists(docx_file):
                docx_file = f"{docx_directory}/{h} ({i}).docx"
                i += 1
            with open(docx_file, "wb") as f:
                f.write(docx_bytes)

            return {
                "final_document": document_text,
                "document_path": docx_file,
                "pipeline_status": "completed",
            }

        except Exception as e:
            logger.error("DOCX generation failed: %s", e, exc_info=True)
            return {
                "final_document": document_text,
                "document_path": "",
                "pipeline_status": "completed_with_errors",
                "error": f"Ошибка генерации DOCX: {str(e)}",
            }

    async def process_user_message(
        self,
        user_message: str,
        thread_id: str,
        user_metadata: dict[str, Any]={},
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
            initial_state["user_metadata"] = user_metadata

            config = {"configurable": {"thread_id": thread_id}}

            with collect_runs() as runs_cb:
                final_state = await asyncio.to_thread(
                    self.graph.invoke,
                    initial_state,
                    config,
                )
            root_run = runs_cb.traced_runs[-1]


            usage = final_state.get("usage_metadata", {}) or {}
            metadata = {
                "run_id": str(root_run.id),
                "trace_id": str(root_run.trace_id),
                "latency_ms": int((root_run.end_time - root_run.start_time).total_seconds() * 1000),
                "input_tokens": int(usage.get("input_tokens", 0) or 0),
                "output_tokens": int(usage.get("output_tokens", 0) or 0),
                "total_tokens": int(usage.get("total_tokens", 0) or 0),
            }
            
            response = self._format_response(final_state)
            response["metadata"] = metadata
            return response

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

        document_path = state.get("document_path", "")
        if document_path:
            logger.debug(f"Got document path: {document_path}")
            return {
                "reply": document_path,
                "handled_by_agent": True,
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
