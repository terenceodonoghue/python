# CLAUDE.md

## What is this?

A Python workspace managed by **uv**, with projects in `projects/*`.

- **solar-cli** (`projects/solar-cli`) — CLI agent that queries solar production data in InfluxDB using Claude's tool-use API

## Commands

Use **uv** (not pip/pipx/poetry).

- Lint: `uv run ruff check`
- Lint (auto-fix): `uv run ruff check --fix`
- Format: `uv run ruff format`
- Run solar-cli locally: `cd projects/solar-cli && uv run solar-cli --verbose`
- Build solar-cli image: `docker build -t solar-cli:latest projects/solar-cli`

## Conventions

- Python 3.13+
- Projects live in `projects/`, each with its own `pyproject.toml` and `Dockerfile`
- Commit messages use imperative present tense (e.g., "Add feature", "Fix bug")

## Code style

Handled entirely by Ruff — do not manually enforce formatting rules.
Import order is enforced by Ruff's isort rules.
