import logging

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Конфигурация приложения.
    """
    
    # Приложение
    APP_NAME: str = "AI Lawyer Inference Server"
    APP_VERSION: str = "1.0.0"
    MODE: str = "DEBUG"
    
    # LLM
    LLM_MODEL: str = "GigaChat"
    
    # Логирование
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Игнорировать дополнительные поля


settings = Settings()

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

