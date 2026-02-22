# solar-cli

CLI agent that queries solar production data in InfluxDB using natural language. Powered by Claude's tool-use API.

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- Docker and Docker Compose
- An Anthropic API key
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

Run the CLI:

```sh
INFLUX_URL=http://localhost:8086 \
INFLUX_TOKEN=dev-token \
INFLUX_ORG=homelab \
ANTHROPIC_API_KEY=your-key \
uv run solar-cli
```

Use `--verbose` to print the generated Flux queries.

## Configuration

| Variable | Description | Example |
|---|---|---|
| `INFLUX_URL` | InfluxDB base URL | `http://localhost:8086` |
| `INFLUX_TOKEN` | InfluxDB API token with read access | `dev-token` (local) |
| `INFLUX_ORG` | InfluxDB organisation (optional, defaults to `homelab`) | `homelab` |
| `ANTHROPIC_API_KEY` | Anthropic API key | `sk-ant-...` |

All variables are required except `INFLUX_ORG`.

## How it works

Solar CLI uses Claude's [tool use](https://docs.anthropic.com/en/docs/build-with-claude/tool-use) capability. When you ask a question:

1. Claude receives your question along with a system prompt describing the InfluxDB schema (buckets, fields, retention policies)
2. Claude writes a Flux query and calls the `query_influxdb` tool
3. The tool executes the query against InfluxDB and returns the results as JSON
4. Claude interprets the data and responds in plain English

Claude can make multiple queries per question (up to 5) and maintains conversation history within a session, so follow-up questions work naturally.

## Docker

Build the image:

```sh
docker build -t solar-cli:latest .
```

Run interactively:

```sh
docker run --rm -it \
  -e INFLUX_URL=http://influxdb:8086 \
  -e INFLUX_TOKEN="$INFLUX_TOKEN" \
  -e INFLUX_ORG="$INFLUX_ORG" \
  -e ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  solar-cli:latest
```
