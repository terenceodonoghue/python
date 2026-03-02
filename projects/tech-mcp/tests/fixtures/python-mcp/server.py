"""Mock MCP server for testing introspection."""

import json
import os

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "test-mcp",
    host=os.environ.get("MCP_HOST", "0.0.0.0"),
    port=int(os.environ.get("MCP_PORT", "9000")),
)


@mcp.tool()
def query_metrics(query: str, bucket: str = "default") -> str:
    """Query time-series metrics from the database.

    Executes a query against the metrics store and returns results
    as JSON.

    Args:
        query: The query string to execute.
        bucket: The metrics bucket to query (default: "default").
    """
    return json.dumps({"result": "mock", "query": query, "bucket": bucket})


@mcp.tool()
def check_service_status(service_name: str) -> str:
    """Check if a service is running and healthy.

    Queries the Docker daemon for container status.

    Args:
        service_name: Name of the Docker service to check.
    """
    return json.dumps({"service": service_name, "status": "running"})


@mcp.tool()
def query_influxdb(flux_query: str) -> str:
    """Execute a Flux query against InfluxDB for solar production data.

    The InfluxDB instance stores solar inverter metrics including power
    output, energy production, and voltage readings.

    Args:
        flux_query: A complete Flux query string.
    """
    return json.dumps({"result": "mock"})


@mcp.prompt()
def system_analyst() -> str:
    """Prompt for analysing system health and infrastructure."""
    return "You are a systems analyst."
