FROM python:3.13-slim

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir fastapi uvicorn

CMD ["uvicorn", "src.inference_server.main:app", "--host", "0.0.0.0", "--port", "8000"]