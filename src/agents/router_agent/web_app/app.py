import sys
from pathlib import Path

import fastapi
from fastapi import Request

from ..graph import RouterAgent


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

app = fastapi.FastAPI()
router_agent = RouterAgent()


@app.get("/health")
async def health_check():
    """
    Эндпоинт для проверки работоспособности маршрутизирующего агента.
    """
    return {"status": "ok"}


@app.post("/router_agent")
async def router_agent_endpoint(request: Request):
    """
    Эндпоинт для маршрутизирующего агента.
    
    Принимает POST-запрос с JSON, содержащим:
    - user_message: текст сообщения от пользователя
    """
    data = await request.json()
    user_message = data.get("user_message", "")

    result = await router_agent.process_user_message(user_message)
    
    return {"received_message": user_message}