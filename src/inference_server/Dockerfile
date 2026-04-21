FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/src

RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY src/inference_server/requirements.txt ./

RUN pip install --upgrade pip setuptools wheel && \
    pip install "uvicorn[standard]>=0.30.0" && \
    pip install -r requirements.txt

WORKDIR /app

COPY . /app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/api/chat/health')" || exit 1

CMD ["python", "-m", "uvicorn", "src.inference_server.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
