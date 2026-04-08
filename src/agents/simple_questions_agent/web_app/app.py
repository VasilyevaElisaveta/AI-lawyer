import sys
from pathlib import Path
from pydantic import BaseModel

import fastapi

from ..graph import SimpleQuestionAgent


class MessageRequest(BaseModel):
    user_id: str
    user_message: str


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

app = fastapi.FastAPI()
simple_question_agent = SimpleQuestionAgent()


@app.get("/health")
async def health_check():
    """
    Эндпоинт для проверки работоспособности агента по простым вопросам.
    """
    return {"status": "ok"}


@app.post("/simple_question_agent")
async def simple_question_agent_endpoint(request: MessageRequest):
    result = await simple_question_agent.process_user_message(
        user_message=request.user_message,
        thread_id=request.user_id,
    )
    return {
        "request": request,
        "response": result
    }