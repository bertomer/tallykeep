# Single image for both backend (FastAPI) and worker entry points.
# Runtime command is selected by docker-compose (uvicorn vs python -m tallykeep.worker).
#
# Dev image: installs the [dev] extras so we can run pytest, ruff, mypy from the same
# container without rebuilding for tests. A leaner production image is a v1.x concern.

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# OS deps. Kept minimal; later milestones may add libsecp256k1 for bdkpython.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy project metadata first so Docker layer cache survives source-only edits.
COPY pyproject.toml ./
COPY README.md ./

# Install runtime + dev deps. We rely on hatchling's PEP 517 path; the package itself is
# installed in editable mode after we COPY the source below.
RUN pip install --upgrade pip \
    && pip install \
        "fastapi==0.115.6" \
        "uvicorn[standard]==0.32.1" \
        "pydantic==2.10.3" \
        "pydantic-settings==2.7.0" \
        "structlog==24.4.0" \
        "httpx==0.28.1" \
        "sqlalchemy==2.0.36" \
        "alembic==1.14.0" \
        "psycopg[binary]==3.2.3" \
        "argon2-cffi==23.1.0" \
        "cryptography==44.0.0" \
        "redis==5.2.0" \
        "rq==1.16.2" \
        "bdkpython==2.3.1" \
        "pyzmq==26.2.0" \
        "qrcode[pil]==8.0" \
        "ccxt==4.4.57" \
        "pytest==8.3.4" \
        "pytest-asyncio==0.25.0" \
        "pytest-cov==6.0.0" \
        "ruff==0.8.4" \
        "mypy==1.13.0"

# Source comes last so source edits invalidate fewer cached layers.
COPY alembic.ini ./
COPY tallykeep ./tallykeep
COPY tests ./tests

# Editable install so test runs see the latest source without rebuild.
RUN pip install -e . --no-deps

EXPOSE 8000

# Default to running the API; the worker service overrides via `command:` in compose.
CMD ["uvicorn", "tallykeep.main:app", "--host", "0.0.0.0", "--port", "8000"]
