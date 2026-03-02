# CLAUDE.md

## What is this?

MCP knowledge base server that helps Claude work effectively across multiple related repositories. Stores documentation, source code, and debugging sessions as semantic embeddings in ChromaDB.

## Architecture

- **Transport:** StreamableHTTP via the `mcp` SDK's FastMCP — runs on Starlette
- **Vector store:** ChromaDB in embedded mode (DuckDB+Parquet), single collection with `source` metadata for filtering
- **Embeddings:** Ollama `nomic-embed-text` via httpx (768-dim vectors, cosine similarity)
- **Chunking:** `langchain_text_splitters` — markdown header-aware for docs, language-aware for code
- **No auth:** Caddy is the single auth boundary at the edge. The MCP server trusts all inbound connections. Do not add application-level auth — it would be redundant and inconsistent with the codebydesign.dev infrastructure pattern

## Key Concepts

### Source types in ChromaDB

Every chunk has a `source` metadata field: `doc`, `code`, or `session`. Search tools accept `source_type` to filter.

### Relationship graph

`data/relationships.json` — adjacency list keyed by repo name. Each entry has `type` (service/webapp/infrastructure/mcp/library), optional `mcp_server: true`, and relationship arrays (`consumes`, `consumed_by`, `depends_on`, `hosts`).

`search_related` uses this graph to expand queries to related repos.

### Chunking strategy

- **Markdown:** Split by headers first (preserve heading hierarchy as `heading_context`), then by character count (~2400 chars / ~600 tokens, 400 char overlap)
- **Python/Go/JS/TS:** Language-aware separators, ~1600 chars / ~400 tokens, 320 char overlap
- **Sessions:** Formatted into a fixed markdown template, then chunked as markdown

## How to add a new repo

1. Add entry to `data/relationships.json`
2. Call `ingest_directory(path, repo_name)` to ingest all files

## Caddy setup

In the homelab Caddyfile, `tech.codebydesign.dev` routes `/mcp*` to `tech-mcp:8091`. Both the Tailscale/local block and the Cloudflare tunnel block include this route.

## Ollama from Docker

Inside Docker, `localhost` refers to the container itself. Use:
- `http://host.docker.internal:11434` (Docker Desktop on Mac)
- `http://<Pi-IP>:11434` (direct IP on Linux/Pi)

Never use `http://localhost:11434` from within a container.

## Claude Desktop setup

```json
{
  "mcpServers": {
    "tech-mcp": {
      "command": "npx",
      "args": ["mcp-remote", "https://tech.codebydesign.dev/mcp"]
    }
  }
}
```

## Common failure modes

- **Ollama unreachable from Docker** — most common Pi issue. Verify `OLLAMA_HOST` points to the host IP, not localhost. Test: `docker exec <container> python -c "import httpx; print(httpx.get('http://host.docker.internal:11434/api/tags').json())"`
- **ChromaDB volume permissions** — if the container runs as non-root and the volume was created by root, chown the volume directory
- **mcp-remote connection issues** — check Caddy logs first (`docker compose logs caddy`), then verify DNS resolution for `tech.codebydesign.dev`

## Rollback workflow

1. `list_recent_ingestions()` — find the session ID
2. `forget_session(ingest_session_id)` — remove those chunks
3. Or: `forget_file(path, repo)`, `forget_repo(repo, confirm=True)`

## Commands

- Run locally: `OLLAMA_HOST=http://localhost:11434 PORT=8091 uv run tech-mcp`
- Run tests: `uv run pytest tests/ -v`
- Lint: `uv run ruff check src/`
- Build image: `docker build -t tech-mcp:latest .`

## Phase 2 notes

OAuth 2.1 support for native Claude.ai remote MCP — would allow connecting directly without mcp-remote as the stdio-to-HTTP bridge.
