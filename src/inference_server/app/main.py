import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router
from .core.settings import settings


# Инициализация логирования
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """
    Создаёт и конфигурирует приложение FastAPI.
    """
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
    )
    
    # Добавляем CORS middleware для фронтенда
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Подключаем маршруты
    app.include_router(router, prefix="/api/chat", tags=["chat"])
    
    @app.on_event("startup")
    async def startup_event():
        logger.info(f"=== {settings.APP_NAME} v{settings.APP_VERSION} запущен ===")
        logger.info(f"Debug mode: {settings.DEBUG}")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info(f"=== {settings.APP_NAME} завершил работу ===")
    
    return app


# Создаём приложение
app = create_app()
