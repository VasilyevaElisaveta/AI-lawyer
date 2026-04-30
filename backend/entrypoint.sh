#!/bin/bash
set -e

cd /backend

echo "Applying database migrations..."
uv run alembic upgrade head

echo "Starting application..."
exec uv run app/main.py