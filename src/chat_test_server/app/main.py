from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .api.v1.router import router as api_v1_router
from .core.settings import settings
from .services.agent_client import AgentClient
from .services.chat_service import ChatService


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)

    agent_client = AgentClient(
        base_url=settings.agent_base_url,
        chat_path=settings.agent_chat_path,
        timeout_seconds=settings.agent_timeout_seconds,
    )
    app.state.chat_service = ChatService(agent_client)

    app.include_router(api_v1_router, prefix=settings.api_v1_prefix)

    # подключаем фронт
    app.mount("/static", StaticFiles(directory="app/web"), name="static")

    @app.get("/")
    async def index():
        return FileResponse("app/web/index.html")

    return app


app = create_app()