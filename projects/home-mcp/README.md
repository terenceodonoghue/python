# home-mcp

MCP server that exposes solar production data from InfluxDB. Provides a `query_solar_data` tool for writing and executing Flux queries against solar energy time-series data.

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- Docker and Docker Compose
- A [solar-svc](https://github.com/terenceodonoghue/go/tree/main/services/solar-svc) instance writing data to InfluxDB (or the bundled dev compose)

## Quick start

Start InfluxDB and solar-svc:

```sh
docker compose up -d
```

> solar-svc requires `INVERTER_URL` and `INVERTER_CAPACITY_W` — set them in a `.env` file or export them before running `docker compose up`.

Install dependencies:

```sh
uv sync
```

Run the MCP server (stdio transport for local development):

```sh
INFLUX_URL=http://localhost:8086 \
INFLUX_TOKEN=dev-token \
INFLUX_ORG=my-org \
uv run home-mcp
```

### Claude Code

Add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "home-mcp": {
      "command": "uv",
      "args": ["run", "--project", "/path/to/projects/home-mcp", "home-mcp"],
      "env": {
        "INFLUX_URL": "http://localhost:8086",
        "INFLUX_TOKEN": "dev-token",
        "INFLUX_ORG": "my-org"
      }
    }
  }
}
```

### Claude Desktop

Add to Claude Desktop settings (Settings > Developer > Edit Config):

```json
{
  "mcpServers": {
    "home-mcp": {
      "command": "uv",
      "args": ["run", "--project", "/path/to/projects/home-mcp", "home-mcp"],
      "env": {
        "INFLUX_URL": "http://localhost:8086",
        "INFLUX_TOKEN": "dev-token",
        "INFLUX_ORG": "my-org"
      }
    }
  }
}
```

For a remote server (e.g., behind a reverse proxy), use [`mcp-remote`](https://www.npmjs.com/package/mcp-remote) to bridge HTTP to stdio:

```json
{
  "mcpServers": {
    "home-mcp": {
      "command": "npx",
      "args": ["mcp-remote", "https://mcp.example.com/mcp"]
    }
  }
}
```

## Configuration

| Variable | Description | Default |
|---|---|---|
| `INFLUX_URL` | InfluxDB base URL | *(required)* |
| `INFLUX_TOKEN` | InfluxDB API token with read access | *(required)* |
| `INFLUX_ORG` | InfluxDB organisation | *(required)* |
| `MCP_TRANSPORT` | MCP transport: `stdio`, `streamable-http`, or `sse` | `stdio` |
| `MCP_HOST` | Listen address (HTTP transports only) | `0.0.0.0` |
| `MCP_PORT` | Listen port (HTTP transports only) | `8090` |

## How it works

home-mcp exposes an MCP [tool](https://modelcontextprotocol.io/docs/concepts/tools) called `query_solar_data`. When an MCP client (Claude Code, Claude Desktop) needs solar data:

1. The client discovers the `query_solar_data` tool and reads its description, which includes the full InfluxDB schema, query guidelines, and example Flux queries
2. The LLM writes a Flux query and calls the tool
3. home-mcp executes the query against InfluxDB and returns the results as JSON
4. The LLM interprets the data and responds to the user

A `solar_analyst` prompt is also available, providing presentation preferences (unit conversion, rounding) for conversational use.

## Docker

Build the image:

```sh
docker build -t home-mcp:latest .
```

Run with HTTP transport:

```sh
docker run --rm \
  -e INFLUX_URL=http://influxdb:8086 \
  -e INFLUX_TOKEN="$INFLUX_TOKEN" \
  -e INFLUX_ORG="$INFLUX_ORG" \
  -p 8090:8090 \
  home-mcp:latest
```
