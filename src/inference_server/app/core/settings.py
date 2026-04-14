import os
import logging
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Конфигурация приложения.
    """
    
    # Приложение
    APP_NAME: str = "AI Lawyer Inference Server"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Сервер
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # LLM
    LLM_MODEL: str = "GigaChat"
    LLM_TEMPERATURE: float = 0.0
    SBER_AUTH: Optional[str] = None
    
    # Дополнительные поля для GigaChat (игнорируем)
    SBER_ID: Optional[str] = None
    SBER_SECRET: Optional[str] = None
    GIGACHAT_TOKEN: Optional[str] = None
    GIGACHAT_TOKEN_EXPIRES: Optional[str] = None
    
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

