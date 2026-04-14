from typing import Any

from .base import BaseGraphAgent

from .....agents.router_agent import RouterAgent


class RouterGraphAgent(BaseGraphAgent):
    def __init__(self):
        self.agent = RouterAgent()
    
    async def run(self, message: str, thread_id: str) -> dict[str, Any]:
        """
        Запускает router agent для классификации запроса.
        
        Returns:
            dict с полями:
            - category: тип запроса (contract, lawsuit, pretrial_claim, simple_question)
            - routed_to: к какому агенту направить запрос
            - classification_confidence: уверенность классификации
        """
        result = await self.agent.process_user_message(message, thread_id)
        
        # Маппируем результат классификации на роут
        category = result.get("category", "simple_question")
        route_mapping = {
            "contract": "contract_agent",
            "lawsuit": "contract_agent",  # Пока используем contract_agent для lawsuit
            "pretrial_claim": "contract_agent",  # Пока используем contract_agent для претензий
            "simple_question": "simple_agent",
        }
        
        return {
            "route": route_mapping.get(category, "simple_agent"),
            "category": category,
            "classification_confidence": result.get("classification_confidence", 0.0),
            "routed_to": route_mapping.get(category, "simple_agent"),
            "handled_by_agent": True,
        }