from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "chat-test-service"
    api_v1_prefix: str = "/api/v1"

    agent_base_url: str = "http://agent:8000"
    agent_chat_path: str = "/chat"
    agent_timeout_seconds: float = 120.0


settings = Settings()