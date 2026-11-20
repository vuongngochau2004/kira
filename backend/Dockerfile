# KIRA backend image (FastAPI API server + Celery worker share this image)
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /uvx /bin/

# Dependencies first for layer caching. uv.lock is gitignored, so fall back to resolving.
COPY pyproject.toml uv.lock* ./
RUN if [ -f uv.lock ]; then uv sync --frozen --no-install-project; \
    else uv sync --no-install-project; fi

COPY kira/ kira/

RUN mkdir -p logs reports

EXPOSE 8006
CMD ["uvicorn", "kira.main:app", "--host", "0.0.0.0", "--port", "8006"]
