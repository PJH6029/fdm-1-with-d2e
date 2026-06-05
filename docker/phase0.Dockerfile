# Phase 0 local/MLXP smoke image for fdm-1-with-d2e.
# This image intentionally contains only CPU/offline data-pipeline dependencies.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/fdm-1-with-d2e/.venv \
    PATH="/opt/fdm-1-with-d2e/.venv/bin:/root/.local/bin:${PATH}"

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv==0.9.13

WORKDIR /opt/fdm-1-with-d2e

COPY pyproject.toml uv.lock ./
COPY src ./src
COPY scripts ./scripts
COPY configs ./configs
COPY schemas ./schemas
COPY tests ./tests

RUN uv sync --locked --group dev \
    && uv run --locked pytest tests/smoke tests/unit/test_bootstrap_configs.py

CMD ["sleep", "infinity"]
