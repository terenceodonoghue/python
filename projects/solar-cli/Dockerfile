FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml README.md ./
RUN uv sync --no-dev --no-install-project

COPY src/ src/
RUN uv sync --no-dev

ENTRYPOINT [".venv/bin/solar-cli"]
