# Dockerfile for Contract Agent FastAPI app
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN python -m pip install --upgrade pip
RUN python -m pip install fastapi uvicorn python-dotenv langchain-gigachat langchain-core

COPY ./src /app/src

WORKDIR /app/src/agents/contract_agent/web_app

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
