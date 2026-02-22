# solar-cli

CLI agent that queries solar production data in InfluxDB using natural language. Powered by Claude's tool-use API.

## Prerequisites

- Python 3.13+
- Docker
- An Anthropic API key
- Access to an InfluxDB 2.x instance with solar data (written by [solar-svc](https://github.com/terenceodonoghue/go/tree/main/services/solar-svc))

## Quick start

Build the Docker image:

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

Use `--verbose` to print the generated Flux queries:

```sh
docker run --rm -it \
  -e INFLUX_URL=http://influxdb:8086 \
  -e INFLUX_TOKEN="$INFLUX_TOKEN" \
  -e INFLUX_ORG="$INFLUX_ORG" \
  -e ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  solar-cli:latest --verbose
```

## Configuration

| Variable | Description | Example |
|---|---|---|
| `INFLUX_URL` | InfluxDB base URL | `http://influxdb:8086` |
| `INFLUX_TOKEN` | InfluxDB API token with read access | |
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

## Local development

Install dependencies:

```sh
uv sync
```

Run directly:

```sh
export INFLUX_URL=http://localhost:8086
export INFLUX_TOKEN=your-token
export ANTHROPIC_API_KEY=your-key
uv run solar-cli --verbose
```
