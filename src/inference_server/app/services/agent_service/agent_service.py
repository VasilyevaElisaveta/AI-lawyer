import os

from logger import LoggerFactory

from agents.llm_client import create_gigachat, DEFAULT_GIGACHAT_PARAMS

from .agents.contract_agent import ContractGraphAgent
from .agents.claims_agent import ClaimsGraphAgent
from .agents.general_questions_agent import GeneralQuestionsGraphAgent
from .agents.router_agent import RouterGraphAgent

from ...schemas.chat import ChatRequest, ChatResponse


logger = LoggerFactory.get_logger(
    name=__name__,
    logs_path=os.getenv("LOGS_DIR"),
    log_file=os.getenv("LOGS_FILE") if os.getenv("MODE") != "DEBUG" else None,
)


def check_error(result):
    error = result.get("error", None)
    if error:
        raise Exception(error)


class AgentService:
    """
    Сервис для управления всеми агентами инференс сервера.
    
    Использует router agent для классификации запроса, затем маршрутизирует
    к соответствующему агенту (contract_agent, general_agent).
    """
    
    def __init__(self):
        logger.info("Инициализация AgentService...")
        router_config={
            "metadata": {
                "ls_provider": "gigachat",
                "ls_model_name": "GigaChat",
            }
        }
        router_kwargs = {
            "credentials": os.getenv("SBER_AUTH"),
            **DEFAULT_GIGACHAT_PARAMS
        }
        contract_config={
            "metadata": {
                "ls_provider": "gigachat",
                "ls_model_name": "GigaChat",
            }
        }
        contract_kwargs = {
            "credentials": os.getenv("SBER_AUTH"),
            **DEFAULT_GIGACHAT_PARAMS
        }
        contract_generator_config={
            "metadata": {
                "ls_provider": "gigachat",
                "ls_model_name": "GigaChat",
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
                "ls_model_name": "GigaChat",
            }
        }
        claims_kwargs = {
            "credentials": os.getenv("SBER_AUTH"),
            **DEFAULT_GIGACHAT_PARAMS
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
                "ls_model_name": "GigaChat",
            }
        }
        general_questions_kwargs = {
            "credentials": os.getenv("SBER_AUTH"),
            **DEFAULT_GIGACHAT_PARAMS
        }

        router_llm = create_gigachat("GigaChat", config=router_config, **router_kwargs)
        contract_llm = create_gigachat("GigaChat", config=contract_config, **contract_kwargs)
        contract_generator_llm = create_gigachat("GigaChat", config=contract_generator_config, **contract_generator_kwargs)
        claims_llm = create_gigachat("GigaChat", config=claims_config, **claims_kwargs)
        general_questions_llm = create_gigachat("GigaChat", config=general_questions_config, **general_questions_kwargs)

        self.router_agent = RouterGraphAgent(router_llm)
        self.contract_agent = ContractGraphAgent(contract_llm, generator_llm=contract_generator_llm)
        self.claims_agent = ClaimsGraphAgent(claims_llm)
        self.general_questions_agent = GeneralQuestionsGraphAgent(general_questions_llm)
        logger.info("AgentService инициализирован успешно")

    async def process(self, request: ChatRequest) -> ChatResponse:
        """
        Обрабатывает запрос пользователя через router или прямой агент.
        
        Args:
            request: ChatRequest с raw_input, thread_id и optional agent_type
            
        Returns:
            ChatResponse с reply и метаданными
        """
        try:
            if request.agent_type:
                logger.info(f"Явно указан агент: {request.agent_type}")
                agent = self._get_agent(request.agent_type)
                if agent is None:
                    return ChatResponse(
                        reply=f"Неизвестный тип агента: {request.agent_type}",
                        handled_by_agent=False,
                        document_created=False,
                        is_error=True,
                    )
                result = await agent.run(request.raw_input, request.thread_id)
                return self._to_response(result)

            logger.info("Использование router agent для классификации...")
            route_result = await self.router_agent.run(request.raw_input, request.thread_id)

            route = route_result.get("routed_to", "general_questions_agent")

            check_error(route_result)
            
            logger.info(f"Запрос классифицирован как: {route}")

            if route == "contract_agent":
                logger.info("Маршрутизация на contract_agent...")
                result = await self.contract_agent.run(request.raw_input, request.thread_id)
            if route == "claims_agent":
                logger.info("Маршрутизация на claims_agent...")
                result = await self.claims_agent.run(
                    request.raw_input,
                    request.thread_id, 
                    user_metadata=request.user_metadata
                )
            elif route == "general_questions_agent":
                logger.info("Маршрутизация на general_agent...")
                result = await self.general_questions_agent.run(request.raw_input, request.thread_id)
            else:
                logger.warning(f"Неизвестный маршрут: {route}, используем general_questions_agent")
                result = await self.general_questions_agent.run(request.raw_input, request.thread_id)
            
            check_error(result)

            response = self._to_response(result)
            logger.info(f"Ответ готов: {len(response.reply)} символов")
            return response
            
        except Exception as e:
            logger.error(f"Ошибка при обработке запроса: {str(e)}", exc_info=True)
            return ChatResponse(
                reply=f"Ошибка при обработке запроса: {str(e)}",
                handled_by_agent=False,
                document_created=False,
                is_error=True
            )

    def _get_agent(self, agent_type: str):
        mapping = {
            "contract_agent": self.contract_agent,
            "general_questions_agent": self.general_questions_agent,
            "claims_agent": self.claims_agent,
            "router_agent": self.router_agent,
        }
        return mapping.get(agent_type.lower(), None)

    def _to_response(self, result: dict) -> ChatResponse:
        metadata = result.get("metadata", {})
        return ChatResponse(
            reply=result.get("reply", ""),
            handled_by_agent=result.get("handled_by_agent", True),
            document_created=result.get("document_created", False),
            is_error=result.get("is_error", False),
            latency_ms=metadata.get("latency_ms", 0),
            input_tokens=metadata.get("input_tokens", 0),
            output_tokens=metadata.get("output_tokens", 0),
            total_tokens=metadata.get("total_tokens", 0),
            run_id=metadata.get("run_id"),
            trace_id=metadata.get("trace_id"),
            process_name=metadata.get("process_name", "unknown_process")
        )