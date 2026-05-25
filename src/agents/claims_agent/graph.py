"""
Агент для генерации исковых заявлений и претензий.
"""
import os
from typing import Any, AsyncIterator
from logger import LoggerFactory

from langchain_core.tracers.context import collect_runs

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableConfig

from .state import ClaimsAgentState
from .session import session_reset_values
from .nodes import (
    intake_node,
    classification_node,
    validation_node,
    research_node,
    calculator_node,
    generator_node,
    qa_node,
    pre_generation_notify_node,
    document_comment_node,
    evaluate_continue_task,
)
from .utils.docx_generator import (
    build_docx_filename,
    generate_docx_bytes,
    resolve_unique_docx_path,
    save_docx_file,
)

from ..utils import resolve_run_usage, state_int


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

    async def get_current_agent(self, thread_id: str) -> str | None:
        config = {"configurable": {"thread_id": thread_id}}
        snapshot = await self.graph.aget_state(config)
        if not snapshot or not snapshot.values:
            return None
        return snapshot.values.get("current_agent")

    async def check_continue_task(self, raw_input: str, thread_id: str) -> bool:
        config = {"configurable": {"thread_id": thread_id}}
        snapshot = await self.graph.aget_state(config)
        session_state = snapshot.values if snapshot else {}
        result = await evaluate_continue_task(
            raw_input,
            session_state,
            self.llm,
            config=config,
        )
        return bool(result.get("continue_current_task", False))

    async def _reset_usage_counters(self, config: dict) -> None:
        snapshot = await self.graph.aget_state(config)
        if snapshot and snapshot.values:
            await self.graph.aupdate_state(
                config=config,
                values={"usage_metadata": {}},
                as_node="intake",
            )

    async def clear_session(self, thread_id: str) -> None:
        config = {"configurable": {"thread_id": thread_id}}
        snapshot = await self.graph.aget_state(config)
        if snapshot and snapshot.values:
            await self.graph.aupdate_state(
                config=config,
                values=session_reset_values(),
                as_node="intake",
            )
        logger.info("Claims session cleared for thread %s", thread_id)

    def _build_graph(self, llm) -> Any:
        """Строит граф обработки."""

        def intake_node_wrapper(state: ClaimsAgentState, config: RunnableConfig):
            return intake_node(state, llm, config)
        
        def case_analysis_node_wrapper(state: ClaimsAgentState, config: RunnableConfig):
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

        async def pre_generation_notify_wrapper(
            state: ClaimsAgentState, config: RunnableConfig,
        ):
            return await pre_generation_notify_node(state, llm, config)

        async def document_comment_wrapper(
            state: ClaimsAgentState, config: RunnableConfig,
        ):
            return await document_comment_node(state, llm, config)

        builder = StateGraph(ClaimsAgentState)

        # Узлы
        builder.add_node("intake", intake_node_wrapper)
        builder.add_node("case_analysis", case_analysis_node_wrapper)
        builder.add_node("validation", validation_node_wrapper)
        builder.add_node("pre_generation_notify", pre_generation_notify_wrapper)
        builder.add_node("research", research_node_wrapper)
        builder.add_node("calculator", calculator_node_wrapper)
        builder.add_node("generator", generator_node_wrapper)
        builder.add_node("qa", qa_node_wrapper)
        builder.add_node("finalize", _finalize_node_wrapper)
        builder.add_node("document_comment", document_comment_wrapper)

        # Рёбра
        builder.set_entry_point("intake")
        builder.add_edge("intake", "validation")
        builder.add_conditional_edges(
            "validation",
            self._route_after_validation,
            {
                "pre_generation_notify": "pre_generation_notify",
                "intake": "intake",
                END: END,
            },
        )
        builder.add_edge("pre_generation_notify", "case_analysis")
        builder.add_edge("case_analysis", "research")

        builder.add_edge("research", "calculator")
        builder.add_edge("calculator", "generator")
        builder.add_edge("generator", "qa")

        # Условная маршрутизация после QA
        builder.add_conditional_edges(
            "qa",
            self._route_after_qa,
            {"finalize": "finalize", "generator": "generator"},
        )

        builder.add_conditional_edges(
            "finalize",
            self._route_after_finalize,
            {"document_comment": "document_comment", END: END},
        )
        builder.add_edge("document_comment", END)

        return builder.compile(checkpointer=self.memory)

    def _route_after_validation(self, state: ClaimsAgentState) -> str:
        if state.get("is_valid", False):
            logger.info("[claims] обязательные поля заполнены — анализ дела и генерация")
            return "pre_generation_notify"
        attempts = state_int(state, "validation_attempts", 0)
        has_raw = bool(state.get("raw_input"))
        if has_raw and attempts < 2:
            logger.info("[claims] повтор intake (попытка %d)", attempts)
            return "intake"
        logger.info(
            "[claims] остановка: ждём данные от пользователя — %s",
            state.get("validation_errors", []),
        )
        return END

    def _route_after_finalize(self, state: ClaimsAgentState) -> str:
        """После finalize: если документ сохранён — генерируем сопроводительное сообщение."""
        if state.get("document_path"):
            return "document_comment"
        return END

    def _route_after_qa(self, state: ClaimsAgentState) -> str:
        """Маршрутизация после QA."""
        if state.get("qa_passed", False):
            return "finalize"

        attempts = state_int(state, "qa_attempts", 0)
        if attempts < 2:
            logger.info("[claims][qa] повтор генерации (попытка %d)", attempts)
            return "generator"

        logger.info("[claims][qa] лимит попыток — финализация с текущим текстом")
        return "finalize"

    def _finalize_node(self, state: ClaimsAgentState) -> dict[str, Any]:
        """Финализация: генерация DOCX в base64."""
        logger.info("[claims][final] сохранение DOCX")

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
            docx_directory = (
                f"{os.getenv('GENERATED_DOCX_PATH')}/"
                f"{state.get('user_metadata', {}).get('user_id', 'unknown_user')}/"
                f"{state.get('user_metadata', {}).get('thread_id', 'unknown_thread')}"
            )
            os.makedirs(docx_directory, exist_ok=True)
            filename = build_docx_filename(
                document_type,
                state.get("plaintiff_info"),
                state.get("defendant_info"),
            )
            docx_file = resolve_unique_docx_path(docx_directory, filename)
            save_docx_file(docx_bytes, docx_file)
            logger.info(f"DOCX saved: {os.path.basename(docx_file)} ({len(docx_bytes)} bytes)")

            return {
                "final_document": document_text,
                "document_path": docx_file,
                "pipeline_status": "completed",
                "current_agent": None,
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
        logger.info("[claims] сообщение thread=%s", thread_id)

        try:
            import json as _json
            user_metadata = {**(user_metadata or {}), "thread_id": thread_id}
            try:
                input_data = _json.loads(user_message)
                # Тип документа может быть задан внутри JSON-тела
                if "document_type" in input_data:
                    document_type = input_data["document_type"]
                initial_state: dict[str, Any] = {"input_data": input_data}
            except _json.JSONDecodeError:
                initial_state = {"raw_input": user_message}

            initial_state["validation_attempts"] = 0
            initial_state["validation_errors"] = []
            initial_state["qa_attempts"] = 0
            config = {"configurable": {"thread_id": thread_id}}
            await self._reset_usage_counters(config)
            snapshot = await self.graph.aget_state(config)
            prev = snapshot.values if snapshot else {}

            if prev.get("current_agent") == "claims_agent":
                if prev.get("document_type"):
                    document_type = prev["document_type"]
            else:
                if prev:
                    await self.clear_session(thread_id)
                prev = {}

            if document_type not in _DOCUMENT_TYPES:
                logger.warning(
                    "Unknown document_type '%s', falling back to '%s'",
                    document_type,
                    _DEFAULT_DOCUMENT_TYPE,
                )
                document_type = _DEFAULT_DOCUMENT_TYPE

            initial_state["document_type"] = document_type
            initial_state["document_type_locked"] = True
            initial_state["request_id"] = thread_id
            initial_state["user_metadata"] = user_metadata

            with collect_runs() as runs_cb:
                final_state = await self.graph.ainvoke(initial_state, config)
            root_run = runs_cb.traced_runs[-1]


            usage = resolve_run_usage(
                final_state.get("usage_metadata"),
                runs_cb.traced_runs,
            )
            metadata = {
                "run_id": str(root_run.id),
                "trace_id": str(root_run.trace_id),
                "latency_ms": int((root_run.end_time - root_run.start_time).total_seconds() * 1000),
                "input_tokens": usage["input_tokens"],
                "output_tokens": usage["output_tokens"],
                "total_tokens": usage["total_tokens"],
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

    async def astream_user_message(
        self,
        user_message: str,
        thread_id: str,
        user_metadata: dict[str, Any] | None = None,
        document_type: str = _DEFAULT_DOCUMENT_TYPE,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Стриминговый вариант обработки.

        Прокидывает наружу события из custom-канала LangGraph
        (pre_generation_notify_node / document_comment_node), а в конце —
        итоговый result, собранный из финального state с metadata.
        """
        logger.info(f"[claims][stream] сообщение thread={thread_id}")
        user_metadata = {**(user_metadata or {}), "thread_id": thread_id}

        try:
            import json as _json
            try:
                input_data = _json.loads(user_message)
                if "document_type" in input_data:
                    document_type = input_data["document_type"]
                initial_state: dict[str, Any] = {"input_data": input_data}
            except _json.JSONDecodeError:
                initial_state = {"raw_input": user_message}

            initial_state["validation_attempts"] = 0
            initial_state["validation_errors"] = []
            initial_state["qa_attempts"] = 0
            config = {"configurable": {"thread_id": thread_id}}

            await self._reset_usage_counters(config)
            snapshot = await self.graph.aget_state(config)
            prev = snapshot.values if snapshot else {}

            if prev.get("current_agent") == "claims_agent":
                if prev.get("document_type"):
                    document_type = prev["document_type"]
            else:
                if prev:
                    await self.clear_session(thread_id)

            if document_type not in _DOCUMENT_TYPES:
                logger.warning(f"Unknown document_type '{document_type}', falling back to '{_DEFAULT_DOCUMENT_TYPE}'")
                document_type = _DEFAULT_DOCUMENT_TYPE

            initial_state["document_type"] = document_type
            initial_state["document_type_locked"] = True
            initial_state["request_id"] = thread_id
            initial_state["user_metadata"] = user_metadata

            with collect_runs() as runs_cb:
                async for stream_mode, payload in self.graph.astream(
                    initial_state,
                    config=config,
                    stream_mode=["custom", "values"],
                ):
                    if stream_mode == "custom":
                        yield {"channel": "progress", "data": payload}

            final_state = await self.graph.aget_state(config)
            final_values = final_state.values if final_state else {}

            usage = resolve_run_usage(
                final_values.get("usage_metadata"),
                runs_cb.traced_runs,
            )
            root_run = runs_cb.traced_runs[-1] if runs_cb.traced_runs else None
            metadata = {
                "run_id": str(root_run.id) if root_run else "",
                "trace_id": str(root_run.trace_id) if root_run else "",
                "latency_ms": (
                    int((root_run.end_time - root_run.start_time).total_seconds() * 1000)
                    if root_run and root_run.end_time and root_run.start_time
                    else 0
                ),
                "input_tokens": usage["input_tokens"],
                "output_tokens": usage["output_tokens"],
                "total_tokens": usage["total_tokens"],
            }

            response = self._format_response(final_values)
            response["metadata"] = metadata
            yield {"channel": "result", "data": response}

        except Exception as e:
            logger.error("Stream processing failed: %s", e, exc_info=True)
            yield {
                "channel": "result",
                "data": {
                    "reply": f"Произошла ошибка при обработке запроса: {str(e)}",
                    "handled_by_agent": True,
                    "document_created": False,
                    "error": str(e),
                },
            }

    def _format_response(self, state: ClaimsAgentState) -> dict[str, Any]:
        """Форматирование финального ответа."""
        pipeline_status = state.get("pipeline_status", "unknown")
        error = state.get("error", "")
        document_type = state.get("document_type", _DEFAULT_DOCUMENT_TYPE)

        document_path = state.get("document_path") or ""
        if document_path:
            logger.debug(f"Got document path: {document_path}")
            return {
                "reply": document_path,
                "document_comment": state.get("document_comment") or "",
                "handled_by_agent": True,
                "document_created": True,
                "document_type": document_type,
                "status": pipeline_status,
                "task_completed": pipeline_status == "completed",
                "metadata": {
                    "plaintiff": (state.get("plaintiff_info") or "")[:100],
                    "defendant": (state.get("defendant_info") or "")[:100],
                    "total_claim": state.get("total_claim") or 0,
                    "state_duty": state.get("state_duty") or 0,
                },
            }

        if error:
            reply = f"Не удалось создать документ:\n{error}"
        elif state.get("is_valid") is False:
            errors = state.get("validation_errors", [])
            doc_label = "претензии" if document_type == "complaint" else "искового заявления"
            reply = (
                f"Недостаточно данных для создания {doc_label}:\n"
                + "\n".join(f"• {err}" for err in errors)
                + "\n\nПожалуйста, дополните информацию."
            )
        else:
            reply = "Обработка завершена, но документ не был сгенерирован."

        awaiting_input = state.get("current_agent") == "claims_agent"

        return {
            "reply": reply,
            "handled_by_agent": True,
            "document_created": False,
            "document_type": document_type,
            "status": pipeline_status,
            "awaiting_input": awaiting_input,
            "current_agent": state.get("current_agent"),
        }
