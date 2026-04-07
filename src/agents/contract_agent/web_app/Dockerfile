FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN python -m pip install --upgrade pip
RUN python -m pip install fastapi uvicorn python-dotenv langchain-gigachat langchain-core langgraph

COPY ./src /app/src

WORKDIR /app

EXPOSE 8001

CMD ["uvicorn", "src.agents.contract_agent.web_app.app:app", "--host", "0.0.0.0", "--port", "8001"]