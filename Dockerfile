FROM python:3.12-slim

ENV POETRY_VIRTUALENVS_IN_PROJECT=true \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN pip install --no-cache-dir poetry==2.2.1

COPY pyproject.toml poetry.lock README.md alembic.ini ./
COPY payment_service ./payment_service
RUN poetry install --only main --no-interaction --no-ansi

EXPOSE 8000
CMD ["python", "-m", "payment_service.main"]
