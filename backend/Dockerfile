FROM python:3.12-slim

WORKDIR /backend

COPY uv.lock pyproject.toml .python-version ./

RUN pip install uv
RUN uv sync

COPY app ./app
COPY migrations ./migrations
COPY entrypoint.sh alembic.ini .

ENV PYTHONPATH=/backend:/backend/app

RUN chmod +x entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]