# CLAUDE.md

## What is this?

A Python workspace managed by **uv**, with projects in `projects/*`.

Early-stage; no projects yet.

## Commands

Use **uv** (not pip/pipx/poetry).

- Lint: `uv run ruff check`
- Lint (auto-fix): `uv run ruff check --fix`
- Format: `uv run ruff format`

## Conventions

- Python 3.13+
- Projects live in `projects/`
- Commit messages use imperative present tense (e.g., "Add feature", "Fix bug")

## Code style

Handled entirely by Ruff — do not manually enforce formatting rules.
Import order is enforced by Ruff's isort rules.
