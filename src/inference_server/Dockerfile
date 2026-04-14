FROM python:3.13-slim

WORKDIR /app/src/inference_server

COPY . /app

RUN pip install --no-cache-dir fastapi uvicorn

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]