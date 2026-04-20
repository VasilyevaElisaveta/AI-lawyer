import os
import logging
from dotenv import load_dotenv

from .agents.contract_agent import ContractGraphAgent
from .agents.general_agent import GeneralQuestionsGraphAgent
from .agents.router_agent import RouterGraphAgent

from ..schemas.chat import ChatRequest, ChatResponse

from ....agents.llm_client import create_gigachat, DEFAULT_GIGACHAT_PARAMS


logger = logging.getLogger(__name__)
load_dotenv()


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
        general_kwargs = {
            "credentials": os.getenv("SBER_AUTH"),
            **DEFAULT_GIGACHAT_PARAMS
        }

        router_llm = create_gigachat("GigaChat", **router_kwargs)
        contract_llm = create_gigachat("GigaChat", **contract_kwargs)
        general_llm = create_gigachat("GigaChat", **general_kwargs)

        self.router_agent = RouterGraphAgent(router_llm)
        self.contract_agent = ContractGraphAgent(contract_llm)
        self.general_agent = GeneralQuestionsGraphAgent(general_llm)
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
            # Если явно указан тип агента, используем его напрямую
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

            # Иначе используем router для классификации
            logger.info("Использование router agent для классификации...")
            route_result = await self.router_agent.run(request.raw_input, request.thread_id)
            route = route_result.get("routed_to", "general_questions_agent")
            
            logger.info(f"Запрос классифицирован как: {route}")

            # Маршрутизируем к соответствующему агенту
            if route == "contract_agent":
                logger.info("Маршрутизация на contract_agent...")
                result = await self.contract_agent.run(request.raw_input, request.thread_id)
            elif route == "general_questions_agent":
                logger.info("Маршрутизация на general_agent...")
                result = await self.general_agent.run(request.raw_input, request.thread_id)
            else:
                logger.warning(f"Неизвестный маршрут: {route}, используем general_agent")
                result = await self.general_agent.run(request.raw_input, request.thread_id)

            response = self._to_response(result)
            logger.info(f"Ответ готов: {len(response.reply)} символов")
            return response
            
        except Exception as e:
            logger.error(f"Ошибка при обработке запроса: {str(e)}", exc_info=True)
            return ChatResponse(
                reply=f"Ошибка при обработке запроса: {str(e)}",
                handled_by_agent=False,
                document_created=False
            )

    def _get_agent(self, agent_type: str):
        """Возвращает агент по типу."""
        mapping = {
            "contract": self.contract_agent,
            "contract_agent": self.contract_agent,
            "general": self.general_agent,
            "general_agent": self.general_agent,
            "general_question": self.general_agent,
            "router": self.router_agent,
            "router_agent": self.router_agent,
        }
        return mapping.get(agent_type.lower(), None)

    def _to_response(self, result: dict) -> ChatResponse:
        """Преобразует результат агента в ChatResponse."""
        return ChatResponse(
            reply=result.get("reply", ""),
            handled_by_agent=result.get("handled_by_agent", True),
            document_created=result.get("document_created", False)
        )