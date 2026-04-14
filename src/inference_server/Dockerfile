FROM python:3.11-slim

# Установка переменных окружения
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/src

# Установка рабочей директории
WORKDIR /app

# Копирование файлов проекта
COPY . /app

# Установка зависимостей
RUN pip install --upgrade pip setuptools wheel && \
    pip install -e src/inference_server && \
    pip install uvicorn[standard]>=0.30.0

# Expose порт
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/api/chat/health')" || exit 1

# Запуск приложения
CMD ["python", "-m", "uvicorn", "src.inference_server.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
