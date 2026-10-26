FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Git is used by patch-analysis tooling that inspects repository metadata.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/ /app/backend/
COPY schemas/ /app/schemas/
COPY config/vulniverse.toml.sample /app/config/vulniverse.toml.sample

WORKDIR /app/backend
ARG INSTALL_DEV=false
RUN if [ "$INSTALL_DEV" = "true" ]; then \
      uv sync --frozen; \
    else \
      uv sync --frozen --no-dev; \
    fi

CMD ["gunicorn", "--workers", "2", "--bind", "0.0.0.0:8000", "wsgi:app"]

# Background processing must not execute arbitrary patches as root.
RUN groupadd --system vulniverse \
    && useradd --system --gid vulniverse --home-dir /app vulniverse \
    && mkdir -p /app/backend/src/instance /app/job-data \
    && chown -R vulniverse:vulniverse /app /opt/venv
USER vulniverse
