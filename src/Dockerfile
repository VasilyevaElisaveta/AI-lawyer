FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN pip install --upgrade pip setuptools wheel build

WORKDIR /build/logger
COPY --from=logger_lib . .

RUN python -m build --wheel

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt
RUN pip install /build/logger/dist/*.whl

COPY . /app

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "inference_server.app.main:app", "--host", "0.0.0.0", "--port", "8000"]