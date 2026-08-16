# 1. Base stage with Python and uv
FROM python:3.14-slim AS base

# Install uv binary from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Enable bytecode compilation & copy mode
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV PYTHONUNBUFFERED=1

# Copy workspace configuration and package definitions first for layer caching
COPY pyproject.toml ./
COPY uv.lock* ./
COPY backend/pyproject.toml ./backend/
COPY agent/pyproject.toml ./agent/
COPY shared/pyproject.toml ./shared/

# Install dependencies (without installing workspace project packages yet)
RUN uv sync --no-install-workspace --package backend

# Copy source codes
COPY backend ./backend
COPY agent ./agent
COPY shared ./shared

# Final sync to install workspace projects in editable mode
RUN uv sync --package backend

# Ensure virtualenv binaries are prioritized in PATH
ENV PATH="/app/.venv/bin:$PATH"

# 2. Development stage (with auto-reload)
FROM base AS development
WORKDIR /app/backend
EXPOSE 8000
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# 3. Production stage (multi-worker)
FROM base AS production
WORKDIR /app/backend
EXPOSE 8000
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
