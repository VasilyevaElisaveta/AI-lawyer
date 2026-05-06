import os
import logging
from dotenv import load_dotenv

from .agents.contract_agent import ContractGraphAgent
from .agents.claims_agent import ClaimsGraphAgent
from .agents.general_questions_agent import GeneralQuestionsGraphAgent
from .agents.router_agent import RouterGraphAgent

from ..schemas.chat import ChatRequest, ChatResponse

from ....agents.llm_client import create_gigachat, DEFAULT_GIGACHAT_PARAMS


logger = logging.getLogger(__name__)
load_dotenv()


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
        router_kwargs = {
            "credentials": os.getenv("SBER_AUTH"),
            **DEFAULT_GIGACHAT_PARAMS
        }
        contract_kwargs = {
            "credentials": os.getenv("SBER_AUTH"),
            **DEFAULT_GIGACHAT_PARAMS
        }
        contract_generator_kwargs = {
            "credentials": os.getenv("SBER_AUTH"),
            **DEFAULT_GIGACHAT_PARAMS,
            "max_tokens":500
        }
        claims_kwargs = {
            "credentials": os.getenv("SBER_AUTH"),
            **DEFAULT_GIGACHAT_PARAMS
        }
        general_questions_kwargs = {
            "credentials": os.getenv("SBER_AUTH"),
            **DEFAULT_GIGACHAT_PARAMS
        }

        router_llm = create_gigachat("GigaChat", **router_kwargs)
        contract_llm = create_gigachat("GigaChat", **contract_kwargs)
        contract_generator_llm = create_gigachat("GigaChat", **contract_generator_kwargs)
        general_questions_llm = create_gigachat("GigaChat", **general_questions_kwargs)
        claims_llm = create_gigachat("GigaChat", **claims_kwargs)

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
                        document_created=False
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
                result = await self.claims_agent.run(request.raw_input, request.thread_id)
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
        return ChatResponse(
            reply=result.get("reply", ""),
            handled_by_agent=result.get("handled_by_agent", True),
            document_created=result.get("document_created", False),
            is_error=False
        )