"""
FastAPI endpoint для агента генерации исковых заявлений и претензий.
"""
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field
import fastapi

from ..graph import ClaimsAgent

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class MessageRequest(BaseModel):
    """Запрос от пользователя."""
    user_id: str
    user_message: str
    document_type: Literal["lawsuit", "complaint"] = Field(
        default="lawsuit",
        description=(
            "Тип генерируемого документа: "
            "'lawsuit' — исковое заявление, "
            "'complaint' — досудебная претензия"
        ),
    )


app = fastapi.FastAPI(
    title="Lawsuit Agent API",
    description="Агент для генерации исковых заявлений и досудебных претензий",
    version="1.1.0",
)

lawsuit_agent = ClaimsAgent()


@app.get("/health")
async def health_check():
    """Проверка работоспособности сервиса."""
    return {"status": "ok", "agent": "lawsuit"}


@app.post("/lawsuit_agent")
async def lawsuit_agent_endpoint(request: MessageRequest):
    """
    Основной endpoint для обработки запросов.

    Args:
        request: {
            "user_id": "123",
            "user_message": "Текст обращения или JSON",
            "document_type": "lawsuit" | "complaint"
        }

    Returns:
        {
            "reply": "base64-строка DOCX или текст ошибки",
            "handled_by_agent": "lawsuit",
            "document_created": true/false,
            "document_type": "lawsuit" | "complaint"
        }
    """
    result = await lawsuit_agent.process_user_message(
        user_message=request.user_message,
        thread_id=request.user_id,
        document_type=request.document_type,
    )

    return {
        "request": {
            "user_id": request.user_id,
            "document_type": request.document_type,
            "message_length": len(request.user_message),
        },
        "response": result,
    }


@app.get("/")
async def root():
    """Корневой endpoint."""
    return {
        "service": "Lawsuit & Complaint Agent",
        "version": "1.1.0",
        "endpoints": {
            "health": "/health",
            "process": "/lawsuit_agent",
        },
        "document_types": {
            "lawsuit": "Исковое заявление в суд",
            "complaint": "Досудебная претензия",
        },
    }
