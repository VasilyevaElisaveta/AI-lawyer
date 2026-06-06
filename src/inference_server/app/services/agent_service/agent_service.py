import os
from typing import AsyncIterator

from logger import LoggerFactory

from agents.common.checkpointer import is_debug_mode
from agents.llm_client import create_gigachat, DEFAULT_GIGACHAT_PARAMS

from .agents.contract_agent import ContractGraphAgent
from .agents.claims_agent import ClaimsGraphAgent
from .agents.general_questions_agent import GeneralQuestionsGraphAgent
from .agents.router_agent import RouterGraphAgent

from ...schemas.chat import ChatAgentRequest, ChatRequest, ChatResponse


logger = LoggerFactory.get_logger(
    name=__name__,
    logs_path=os.getenv("LOGS_DIR"),
    log_file=os.getenv("LOGS_FILE") if os.getenv("MODE") != "DEBUG" else None,
)


def check_error(result):
    error = result.get("error", None)
    if error:
        raise Exception(error)


def merge_run_metadata(*parts: dict) -> dict:
    """Объединяет metadata нескольких агентов (router + claims и т.д.)."""
    merged: dict = {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "latency_ms": 0,
        "run_id": "",
        "trace_id": "",
        "process_name": "unknown_process",
    }
    for part in parts:
        if not part:
            continue
        meta = part.get("metadata") or part
        for key in ("input_tokens", "output_tokens", "total_tokens", "latency_ms"):
            merged[key] += int(meta.get(key, 0) or 0)
        for key in ("run_id", "trace_id", "process_name"):
            if meta.get(key):
                merged[key] = meta[key]
    return merged


class AgentService:
    """
    Сервис для управления всеми агентами инференс сервера.

    Использует router agent для классификации запроса, затем маршрутизирует
    к соответствующему агенту. Активная сессия claims_agent (current_agent)
    обрабатывается до router: проверка продолжения задачи и дополнение полей.
    """
    def __init__(self):
        logger.info("Инициализация AgentService...")
        router_config={
            "metadata": {
                "ls_provider": "gigachat",
                "ls_model_name": os.getenv("LLM_MODEL", "GigaChat"),
            }
        }
        router_kwargs = {
            "credentials": os.getenv("SBER_AUTH"),
            **DEFAULT_GIGACHAT_PARAMS
        }
        contract_config={
            "metadata": {
                "ls_provider": "gigachat",
                "ls_model_name": os.getenv("LLM_MODEL", "GigaChat"),
            }
        }
        contract_kwargs = {
            "credentials": os.getenv("SBER_AUTH"),
            **DEFAULT_GIGACHAT_PARAMS
        }
        contract_generator_config={
            "metadata": {
                "ls_provider": "gigachat",
                "ls_model_name": os.getenv("LLM_MODEL", "GigaChat"),
            }
        }
        contract_generator_kwargs = {
            "credentials": os.getenv("SBER_AUTH"),
            **DEFAULT_GIGACHAT_PARAMS,
            "max_tokens": 500
        }
        claims_config={
            "metadata": {
                "ls_provider": "gigachat",
                "ls_model_name": os.getenv("LLM_MODEL", "GigaChat"),
            }
        }
        claims_kwargs = {
            "credentials": os.getenv("SBER_AUTH"),
            **DEFAULT_GIGACHAT_PARAMS,
            "max_tokens": 4096,
        }
        contract_generator_config={
            "metadata": {
                "ls_provider": "gigachat",
                "ls_model_name": "GigaChat",
            }
        }
        general_questions_config={
            "metadata": {
                "ls_provider": "gigachat",
                "ls_model_name": os.getenv("LLM_MODEL", "GigaChat"),
            }
        }
        general_questions_kwargs = {
            "credentials": os.getenv("SBER_AUTH"),
            **DEFAULT_GIGACHAT_PARAMS,
            "max_tokens": 4096,
        }

        router_llm = create_gigachat(os.getenv("LLM_MODEL", "GigaChat"), config=router_config, **router_kwargs)
        contract_llm = create_gigachat(os.getenv("LLM_MODEL", "GigaChat"), config=contract_config, **contract_kwargs)
        contract_generator_llm = create_gigachat(os.getenv("LLM_MODEL", "GigaChat"), config=contract_generator_config, **contract_generator_kwargs)
        claims_llm = create_gigachat(os.getenv("LLM_MODEL", "GigaChat"), config=claims_config, **claims_kwargs)
        general_questions_llm = create_gigachat(os.getenv("LLM_MODEL", "GigaChat"), config=general_questions_config, **general_questions_kwargs)

        self.router_agent = RouterGraphAgent(router_llm)
        self.contract_agent = ContractGraphAgent(contract_llm, generator_llm=contract_generator_llm)
        self.claims_agent = ClaimsGraphAgent(claims_llm)
        self.general_questions_agent = GeneralQuestionsGraphAgent(general_questions_llm)
        logger.info("AgentService инициализирован успешно")

    async def initialize(self) -> None:
        """Инициализирует Redis Stack индексы (no-op при MODE=DEBUG)."""
        if is_debug_mode():
            logger.info("Checkpointer: MemorySaver (MODE=DEBUG)")
            return
        logger.info("Инициализация Redis checkpointer (общий AsyncRedisSaver, db=0)...")
        await self.claims_agent.agent.initialize_checkpointer()
        logger.info("Checkpointer готов")

    _AGENT_ALIASES: dict[str, str] = {
        "claims": "claims_agent",
        "claim": "claims_agent",
        "claims_agent": "claims_agent",
        "contract": "contract_agent",
        "contract_agent": "contract_agent",
        "general": "general_questions_agent",
        "general_questions": "general_questions_agent",
        "general_questions_agent": "general_questions_agent",
        "router": "router_agent",
        "router_agent": "router_agent",
    }

    def resolve_agent_type(self, agent_type: str) -> str | None:
        key = (agent_type or "").strip().lower()
        return self._AGENT_ALIASES.get(key)

    async def process_routed(self, request: ChatRequest) -> ChatResponse:
        try:
            active_agent = await self.claims_agent.get_current_agent(request.thread_id)
            if active_agent == "claims_agent":
                wants_continue = await self.claims_agent.check_continue_task(
                    request.raw_input,
                    request.thread_id,
                )
                if wants_continue:
                    logger.info("Продолжение сессии claims (дополнение полей)")
                    result = await self.claims_agent.run(
                        request.raw_input,
                        request.thread_id,
                        user_metadata=request.user_metadata,
                    )
                    check_error(result)
                    return self._to_response(result, metadata=result.get("metadata"))

                logger.info("Пользователь сменил тему — сброс сессии claims, маршрутизация")
                await self.claims_agent.clear_session(request.thread_id)

            logger.info("Использование router agent для классификации...")
            route_result = await self.router_agent.run(
                request.raw_input,
                request.thread_id,
            )
            check_error(route_result)

            route = route_result.get("routed_to")
            if not route:
                return ChatResponse(
                    reply=route_result.get("error") or "Не удалось определить агента.",
                    handled_by_agent=False,
                    document_created=False,
                    is_error=True,
                    latency_ms=0,
                    input_tokens=0,
                    output_tokens=0,
                    total_tokens=0,
                    run_id="",
                    trace_id="",
                    process_name="router_agent",
                )

            document_type = route_result.get("document_type")
            logger.info(
                f"Маршрут: {route}, тип документа для claims: {document_type or '—'}"
            )
            if route == "contract_agent":
                # contract_agent отключён во внешнем API: обращаемся к general_questions_agent.
                logger.info("Маршрут contract_agent → general_questions_agent")
                result = await self.general_questions_agent.run(
                    request.raw_input,
                    request.thread_id,
                )
            elif route == "claims_agent":
                logger.info("Маршрутизация на claims_agent...")
                result = await self.claims_agent.run(
                    request.raw_input,
                    request.thread_id,
                    user_metadata=request.user_metadata,
                    document_type=document_type,
                )
            elif route == "general_questions_agent":
                logger.info("Маршрутизация на general_questions_agent...")
                result = await self.general_questions_agent.run(
                    request.raw_input,
                    request.thread_id,
                )
            else:
                logger.warning(f"Неизвестный маршрут: {route}, используем general_questions_agent")
                result = await self.general_questions_agent.run(
                    request.raw_input,
                    request.thread_id,
                )

            check_error(result)
            combined_meta = merge_run_metadata(route_result, result)
            return self._to_response(result, metadata=combined_meta)

        except Exception as e:
            logger.error(f"Ошибка при обработке запроса: {str(e)}", exc_info=True)
            return ChatResponse(
                reply=f"Ошибка при обработке запроса: {str(e)}",
                handled_by_agent=False,
                document_created=False,
                is_error=True,
                latency_ms=0,
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
                run_id="",
                trace_id="",
                process_name="agent_service",
            )

    async def process_with_agent(
        self,
        agent_type: str,
        request: ChatAgentRequest,
    ) -> ChatResponse:
        try:
            if agent_type == "claims_agent":
                req_meta = request.request_metadata or {}
                document_type = req_meta.get("document_type")
                result = await self.claims_agent.run(
                    request.raw_input,
                    request.thread_id,
                    user_metadata=request.user_metadata or {},
                    document_type=document_type,
                )
            elif agent_type == "contract_agent":
                # contract_agent отключён во внешнем API: обращаемся к general_questions_agent.
                logger.info("Прямой вызов contract_agent → general_questions_agent")
                result = await self.general_questions_agent.run(
                    request.raw_input,
                    request.thread_id,
                )
            elif agent_type == "general_questions_agent":
                result = await self.general_questions_agent.run(
                    request.raw_input,
                    request.thread_id,
                )
            elif agent_type == "router_agent":
                result = self._format_router_direct_response(
                    await self.router_agent.run(
                        request.raw_input,
                        request.thread_id,
                    )
                )
            else:
                return ChatResponse(
                    reply=f"Неизвестный тип агента: {agent_type}",
                    handled_by_agent=False,
                    document_created=False,
                    is_error=True,
                    latency_ms=0,
                    input_tokens=0,
                    output_tokens=0,
                    total_tokens=0,
                    run_id="",
                    trace_id="",
                    process_name="agent_service",
                )

            check_error(result)
            return self._to_response(result)
        except Exception as e:
            logger.error(
                f"Ошибка прямого вызова агента {agent_type}: {str(e)}",
                exc_info=True,
            )
            return ChatResponse(
                reply=f"Ошибка при обработке запроса: {str(e)}",
                handled_by_agent=False,
                document_created=False,
                is_error=True,
                latency_ms=0,
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
                run_id="",
                trace_id="",
                process_name=agent_type,
            )

    @staticmethod
    def _format_router_direct_response(route_result: dict) -> dict:
        route = route_result.get("routed_to")
        doc_type = route_result.get("document_type")
        if route:
            reply = f"Классификация: агент={route}"
            if doc_type:
                reply += f", тип документа={doc_type}"
        else:
            reply = route_result.get("error") or "Не удалось классифицировать запрос."
        return {
            "reply": reply,
            "handled_by_agent": True,
            "document_created": False,
            "error": route_result.get("error"),
            "metadata": route_result.get("metadata", {}),
        }

    def _to_response(self, result: dict, metadata: dict | None = None) -> ChatResponse:
        metadata = metadata or result.get("metadata", {})
        return ChatResponse(
            reply=result.get("reply", ""),
            document_comment=result.get("document_comment", ""),
            handled_by_agent=result.get("handled_by_agent", True),
            document_created=result.get("document_created", False),
            is_error=result.get("is_error", False),
            latency_ms=metadata.get("latency_ms", 0),
            input_tokens=metadata.get("input_tokens", 0),
            output_tokens=metadata.get("output_tokens", 0),
            total_tokens=metadata.get("total_tokens", 0),
            run_id=str(metadata.get("run_id")),
            trace_id=str(metadata.get("trace_id")),
            process_name=metadata.get("process_name", "unknown_process")
        )

    async def process_routed_stream(
        self,
        request: ChatRequest,
    ) -> AsyncIterator[dict]:
        """
        Стриминговая версия process_routed.

        Yield-ит словари формата:
          {"type": "progress", "stage": "...", "content": "...", ...}
          {"type": "result",   "reply": ..., "document_created": ..., ...}
          {"type": "error",    "message": "..."}

        Стримятся только события из claims_agent (pre/post-generation).
        Для остальных агентов отдаётся один финальный result.
        """
        try:
            active_agent = await self.claims_agent.get_current_agent(request.thread_id)
            wants_continue = False
            if active_agent == "claims_agent":
                wants_continue = await self.claims_agent.check_continue_task(
                    request.raw_input,
                    request.thread_id,
                )
                if not wants_continue:
                    logger.info(
                        "Stream: пользователь сменил тему — сброс сессии claims",
                    )
                    await self.claims_agent.clear_session(request.thread_id)

            if active_agent == "claims_agent" and wants_continue:
                logger.info("Stream: продолжение сессии claims_agent")
                async for event in self.claims_agent.astream(
                    request.raw_input,
                    request.thread_id,
                    user_metadata=request.user_metadata,
                ):
                    yield _shape_stream_event(event)
                return

            logger.info("Stream: маршрутизация через router_agent")
            route_result = await self.router_agent.run(
                request.raw_input,
                request.thread_id,
            )
            check_error(route_result)
            route = route_result.get("routed_to")
            if not route:
                yield {
                    "type": "error",
                    "message": route_result.get("error") or "Не удалось определить агента.",
                }
                return

            document_type = route_result.get("document_type")
            if route == "claims_agent":
                async for event in self.claims_agent.astream(
                    request.raw_input,
                    request.thread_id,
                    user_metadata=request.user_metadata,
                    document_type=document_type,
                ):
                    if event.get("channel") == "result":
                        # Прибавляем токены router_agent к итоговой метаинформации.
                        result_data = event["data"]
                        result_data["metadata"] = merge_run_metadata(
                            route_result,
                            result_data,
                        )
                        yield _shape_stream_event(event)
                    else:
                        yield _shape_stream_event(event)
                return

            if route == "general_questions_agent":
                async for event in self.general_questions_agent.astream(
                    request.raw_input,
                    request.thread_id,
                ):
                    if event.get("channel") == "result":
                        result_data = event["data"]
                        result_data["metadata"] = merge_run_metadata(
                            route_result,
                            result_data,
                        )
                        yield _shape_stream_event(event)
                    else:
                        yield _shape_stream_event(event)
                return

            # contract_agent / неизвестный маршрут — пока без стрима.
            # if route == "contract_agent":
            #     result = await self.contract_agent.run(
            #         request.raw_input,
            #         request.thread_id,
            #     )
            else:
                logger.warning(
                    "Stream: неизвестный маршрут %s, используем general_questions_agent",
                    route,
                )
                async for event in self.general_questions_agent.astream(
                    request.raw_input,
                    request.thread_id,
                ):
                    if event.get("channel") == "result":
                        result_data = event["data"]
                        result_data["metadata"] = merge_run_metadata(
                            route_result,
                            result_data,
                        )
                        yield _shape_stream_event(event)
                    else:
                        yield _shape_stream_event(event)
                return
        except Exception as e:
            logger.error("Ошибка стриминговой обработки: %s", e, exc_info=True)
            yield {
                "type": "error",
                "message": f"Ошибка при обработке запроса: {str(e)}",
            }

    async def process_with_agent_stream(
        self,
        agent_type: str,
        request: ChatAgentRequest,
    ) -> AsyncIterator[dict]:
        """Прямой вызов агента в режиме стрима (claims_agent, general_questions_agent)."""
        try:
            if agent_type == "claims_agent":
                req_meta = request.request_metadata or {}
                document_type = req_meta.get("document_type")
                async for event in self.claims_agent.astream(
                    request.raw_input,
                    request.thread_id,
                    user_metadata=request.user_metadata or {},
                    document_type=document_type,
                ):
                    yield _shape_stream_event(event)
                return

            if agent_type == "general_questions_agent":
                async for event in self.general_questions_agent.astream(
                    request.raw_input,
                    request.thread_id,
                ):
                    yield _shape_stream_event(event)
                return

            if agent_type == "contract_agent":
                # contract_agent отключён во внешнем API: стримим general_questions_agent.
                logger.info("Stream contract_agent → general_questions_agent")
                async for event in self.general_questions_agent.astream(
                    request.raw_input,
                    request.thread_id,
                ):
                    yield _shape_stream_event(event)
                return

            # router пока без стрима.
            if agent_type == "router_agent":
                result = self._format_router_direct_response(
                    await self.router_agent.run(
                        request.raw_input,
                        request.thread_id,
                    )
                )
            else:
                yield {
                    "type": "error",
                    "message": f"Неизвестный тип агента: {agent_type}",
                }
                return

            check_error(result)
            yield _shape_stream_event({"channel": "result", "data": result})

        except Exception as e:
            logger.error(
                "Ошибка стриминга агента %s: %s", agent_type, e, exc_info=True,
            )
            yield {
                "type": "error",
                "message": f"Ошибка при обработке запроса: {str(e)}",
            }


def _shape_stream_event(event: dict) -> dict:
    """Нормализует внутреннее событие графа к внешнему контракту /invoke/stream."""
    channel = event.get("channel")
    if channel == "progress":
        payload = event.get("data") or {}
        return {
            "type": "progress",
            "stage": payload.get("stage", "progress"),
            "document_type": payload.get("document_type"),
            "content": payload.get("content", ""),
        }
    if channel == "result":
        data = event.get("data") or {}
        metadata = data.get("metadata") or {}
        return {
            "type": "result",
            "reply": data.get("reply", ""),
            "document_comment": data.get("document_comment", ""),
            "handled_by_agent": data.get("handled_by_agent", True),
            "document_created": data.get("document_created", False),
            "is_error": bool(data.get("error")),
            "error": data.get("error"),
            "latency_ms": metadata.get("latency_ms", 0),
            "input_tokens": metadata.get("input_tokens", 0),
            "output_tokens": metadata.get("output_tokens", 0),
            "total_tokens": metadata.get("total_tokens", 0),
            "run_id": str(metadata.get("run_id", "")),
            "trace_id": str(metadata.get("trace_id", "")),
            "process_name": metadata.get("process_name", "unknown_process"),
        }
    return {"type": event.get("type", "progress"), **event}