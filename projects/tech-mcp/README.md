# tech-mcp

MCP knowledge base server for cross-repo context. Provides semantic search across multiple related repositories and stores debugging session summaries.

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- Docker and Docker Compose
- [Ollama](https://ollama.com/) with `nomic-embed-text` model

## Quick start

Pull the embedding model:

```sh
ollama pull nomic-embed-text
```

Install dependencies:

```sh
uv sync
```

Run the MCP server (stdio transport for local development):

```sh
OLLAMA_HOST=http://localhost:11434 \
PORT=8091 \
uv run tech-mcp
```

### Claude Code

Add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "tech-mcp": {
      "command": "uv",
      "args": ["run", "--project", "/path/to/projects/tech-mcp", "tech-mcp"],
      "env": {
        "OLLAMA_HOST": "http://localhost:11434",
        "PORT": "8091"
      }
    }
  }
}
```

### Claude Desktop

For a remote server (via reverse proxy), use [`mcp-remote`](https://www.npmjs.com/package/mcp-remote):

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

If the Caddy layer requires a bearer token, mcp-remote supports `--header "Authorization: Bearer <token>"`, but this is Caddy's concern — the MCP server needs no auth configuration.

## Configuration

| Variable | Description | Default |
|---|---|---|
| `OLLAMA_HOST` | Ollama API URL | *(required)* |
| `OLLAMA_EMBED_MODEL` | Embedding model name | `nomic-embed-text` |
| `CHROMA_PERSIST_DIR` | ChromaDB data directory | `./data/chroma` |
| `RELATIONSHIPS_FILE` | Relationship graph JSON | `./data/relationships.json` |
| `EMBED_BATCH_SIZE` | Texts per embedding batch | `10` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `PORT` | HTTP listen port | *(required)* |
| `MCP_HOST` | HTTP listen address | `0.0.0.0` |
| `MCP_TRANSPORT` | MCP transport: `stdio`, `streamable-http`, `sse` | `stdio` |

## How it works

tech-mcp stores knowledge in ChromaDB (embedded, DuckDB+Parquet) and uses Ollama's `nomic-embed-text` model for semantic embeddings. Content is ingested as one of three source types:

- **doc** — Documentation files (Markdown, YAML, TOML, etc.)
- **code** — Source code files (Python, Go, TypeScript, etc.)
- **session** — Debugging session summaries (structured problem/solution format)

A relationship graph (`data/relationships.json`) tracks how repos relate to each other, enabling cross-repo search expansion.

## CLI ingestion

```sh
OLLAMA_HOST=http://localhost:11434 PORT=8091 \
python scripts/ingest_repo.py /path/to/repo repo-name
```

## Docker

Build the image:

```sh
docker build -t tech-mcp:latest .
```

Run with HTTP transport:

```sh
docker run --rm \
  -e OLLAMA_HOST=http://host.docker.internal:11434 \
  -e PORT=8091 \
  -v tech_mcp_data:/app/data \
  -p 8091:8091 \
  tech-mcp:latest
```

## Tests

```sh
uv run pytest tests/ -v
```

The eval harness in `tests/test_retrieval.py` runs 8 cases across single-repo, cross-repo, and session queries.
