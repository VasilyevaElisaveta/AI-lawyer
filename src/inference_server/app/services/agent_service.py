import logging
from typing import Any

from .agents.contract_agent import ContractGraphAgent
from .agents.simple_agent import SimpleAgent
from .agents.router_agent import RouterGraphAgent

from ..schemas.chat import ChatRequest, ChatResponse


logger = logging.getLogger(__name__)


class AgentService:
    """
    Сервис для управления всеми агентами инференс сервера.
    
    Использует router agent для классификации запроса, затем маршрутизирует
    к соответствующему агенту (contract_agent, simple_agent).
    """
    
    def __init__(self):
        logger.info("Инициализация AgentService...")
        self.router_agent = RouterGraphAgent()
        self.contract_agent = ContractGraphAgent()
        self.simple_agent = SimpleAgent()
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
            route = route_result.get("route", "simple_agent")
            category = route_result.get("category", "simple_question")
            
            logger.info(f"Запрос классифицирован как: {category}, маршрут: {route}")

            # Маршрутизируем к соответствующему агенту
            if route == "contract_agent":
                logger.info("Маршрутизация на contract_agent...")
                result = await self.contract_agent.run(request.raw_input, request.thread_id)
            elif route == "simple_agent":
                logger.info("Маршрутизация на simple_agent...")
                result = await self.simple_agent.run(request.raw_input, request.thread_id)
            else:
                logger.warning(f"Неизвестный маршрут: {route}, используем simple_agent")
                result = await self.simple_agent.run(request.raw_input, request.thread_id)

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
            "simple": self.simple_agent,
            "simple_agent": self.simple_agent,
            "simple_question": self.simple_agent,
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