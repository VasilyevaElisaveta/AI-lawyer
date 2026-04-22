FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY src/chat_test_server/requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install -r requirements.txt

COPY . /app

EXPOSE 8000

CMD ["uvicorn", "src.chat_test_server.app.main:app", "--host", "0.0.0.0", "--port", "8000"]