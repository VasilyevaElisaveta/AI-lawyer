FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

# Установка зависимостей
RUN python -m pip install --upgrade pip
RUN python -m pip install \
    fastapi \
    uvicorn \
    python-dotenv \
    langchain-gigachat \
    langchain-core \
    langgraph \
    python-docx \
    pydantic

# Копируем код
COPY ./src /app/src

WORKDIR /app

# Открываем порт
EXPOSE 8003

# Запуск (предполагается, что структура src/agents/lawsuit_agent/web_app/app.py)
CMD ["uvicorn", "src.agents.lawsuit_agent.web_app.app:app", "--host", "0.0.0.0", "--port", "8003"]