import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from logger import LoggerFactory

from agents.llm_client import DEFAULT_GIGACHAT_PARAMS

from .api.routes import router
from .core.settings import settings
from .services import AgentService, LLMService


logger = LoggerFactory.get_logger(
    name=__name__,
    logs_path=os.getenv("LOGS_DIR"),
    log_file=os.getenv("LOGS_FILE") if os.getenv("MODE") != "DEBUG" else None,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"=== {settings.APP_NAME} v{settings.APP_VERSION} запущен ===")
    from agents.common.checkpointer import is_debug_mode

    logger.info(
        "MODE=%s (checkpointer: %s)",
        settings.MODE,
        "MemorySaver" if is_debug_mode() else "Redis",
    )
    agent_service = AgentService()
    await agent_service.initialize()
    app.state.agent_service = agent_service

    llm_config={
        "metadata": {
            "ls_provider": "gigachat",
            "ls_model_name": "GigaChat",
        }
    }
    llm_kwargs = {
        "credentials": os.getenv("SBER_AUTH", ""),
        "scope": os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS"),
        **DEFAULT_GIGACHAT_PARAMS,
        "streaming": False,
    }
    app.state.llm_service = LLMService(
        os.getenv("LLM_MODEL", "GigaChat"),
        llm_config,
        **llm_kwargs,
    )

    try:
        yield
    finally:
        logger.info(f"=== {settings.APP_NAME} завершил работу ===")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        debug=settings.MODE.strip().upper() == "DEBUG",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router, prefix="/api/chat")
    return app


app = create_app()