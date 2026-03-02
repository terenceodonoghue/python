# CLAUDE.md

## What is this?

A Python workspace managed by **uv**, with projects in `projects/*`.

- **home-mcp** (`projects/home-mcp`) — MCP server that exposes solar production data from InfluxDB as a tool
- **tech-mcp** (`projects/tech-mcp`) — MCP knowledge base server for cross-repo context, debugging sessions, and MCP interface docs

## Commands

- First-time setup: `make setup` (installs Homebrew tools, syncs uv dependencies, and installs pre-commit hooks)

Use **uv** (not pip/pipx/poetry).

- Lint: `uv run ruff check`
- Lint (auto-fix): `uv run ruff check --fix`
- Format: `uv run ruff format`
- Run home-mcp locally: `cd projects/home-mcp && uv run home-mcp`
- Build home-mcp image: `docker build -t home-mcp:latest projects/home-mcp`
- Run tech-mcp locally: `cd projects/tech-mcp && OLLAMA_HOST=http://localhost:11434 PORT=8091 uv run tech-mcp`
- Build tech-mcp image: `docker build -t tech-mcp:latest projects/tech-mcp`
- Run tech-mcp tests: `cd projects/tech-mcp && uv run pytest tests/ -v`

## Conventions

- Python 3.13+
- Projects live in `projects/`, each with its own `pyproject.toml` and `Dockerfile`
- Commit messages use imperative present tense (e.g., "Add feature", "Fix bug")

## CI

- `home-mcp.yml` — security scan (Gitleaks, CodeQL), Docker build, Trivy image scan, and publish to ghcr.io on push to main (path-filtered to `projects/home-mcp/**`)
- `tech-mcp.yml` — same pipeline for tech-mcp (path-filtered to `projects/tech-mcp/**`)

## Code style

Handled entirely by Ruff — do not manually enforce formatting rules.
Import order is enforced by Ruff's isort rules.
