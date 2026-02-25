import json
import os

from influxdb_client import InfluxDBClient
from influxdb_client.rest import ApiException
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "home-mcp",
    host=os.environ.get("MCP_HOST", "0.0.0.0"),
    port=int(os.environ.get("MCP_PORT", "8090")),
)

_influx = InfluxDBClient(
    url=os.environ["INFLUX_URL"],
    token=os.environ["INFLUX_TOKEN"],
    org=os.environ["INFLUX_ORG"],
)


@mcp.tool()
def query_solar_data(query: str) -> str:
    """Query solar production data from InfluxDB using Flux.

    Returns tabular results as a JSON list of records, each with _time,
    _field, and _value.

    ## InfluxDB Schema

    Organisation: set via INFLUX_ORG env var
    Measurement: inverter
    Tag: device_id = "fronius"

    ### Buckets (choose based on time range)

    - solar-raw: 30-day retention, 5-second granularity. Use for "today",
      "yesterday", "last few days".
    - solar-hourly: 365-day retention, hourly means/last values. Use for
      "last week", "last month".
    - solar-daily: Permanent retention, daily aggregates. Use for "last
      year", "all time", comparisons across months.

    ### Fields

    Instantaneous (aggregated with mean in hourly/daily buckets):
    - pac (W) — AC power output
    - pac_kw (kW) — AC power in kilowatts (prefer this for display)
    - iac (A) — AC current
    - uac (V) — AC voltage
    - fac (Hz) — AC frequency
    - idc (A) — DC current from panels
    - udc (V) — DC voltage from panels
    - utilisation (%) — percentage of rated capacity (8.2 kW inverter)

    Cumulative counters (aggregated with last in hourly/daily buckets):
    - day_energy (Wh) — energy produced today, resets at midnight
    - year_energy (Wh) — energy this calendar year
    - total_energy (Wh) — lifetime energy produced
    - month_energy (Wh) — energy this calendar month (refreshed every 24h)

    No data is written at night or when the inverter is not producing.
    Gaps in the time series are normal. All timestamps are in UTC.

    ## Flux Query Guidelines

    - Always start with: from(bucket: "bucket-name")
    - Always filter: |> filter(fn: (r) => r._measurement == "inverter")
    - Always filter by _field to select specific fields
    - Use range(start: ...) with relative durations (-1d, -7d) or date
      functions (today())
    - For "yesterday": use range(start: -2d, stop: -1d)
    - For peak power: filter for pac_kw, then use max()
    - For total energy in a period: filter for day_energy, use last() per
      day, then sum()
    - The month_energy field is only written when producing, so use
      range(start: -25h) with last() to get the most recent value

    ## Example Queries

    Q: "How much energy did I produce today?"
    from(bucket: "solar-raw")
      |> range(start: today())
      |> filter(fn: (r) => r._measurement == "inverter"
          and r._field == "day_energy")
      |> last()

    Q: "What was peak power today?"
    from(bucket: "solar-raw")
      |> range(start: today())
      |> filter(fn: (r) => r._measurement == "inverter"
          and r._field == "pac_kw")
      |> max()

    Q: "How much energy this month?"
    from(bucket: "solar-raw")
      |> range(start: -25h)
      |> filter(fn: (r) => r._measurement == "inverter"
          and r._field == "month_energy")
      |> last()

    Args:
        query: A complete Flux query string. Must start with
            from(bucket: "..."). Always filter by
            _measurement == "inverter".
    """
    try:
        tables = _influx.query_api().query(query)
    except ApiException as e:
        return json.dumps({"error": e.message})

    records = [
        {
            "_time": r.get_time().isoformat(),
            "_field": r.get_field(),
            "_value": r.get_value(),
        }
        for table in tables
        for r in table.records
    ]

    if not records:
        return json.dumps({"result": "No data found for this query."})
    return json.dumps(records, default=str)


@mcp.prompt()
def solar_analyst() -> str:
    """Prompt for analysing solar production data."""
    return (
        "You are a solar energy data analyst. You answer questions about "
        "solar panel production by querying an InfluxDB time-series "
        "database. Be conversational and helpful.\n\n"
        "Always convert Wh to kWh (divide by 1000) when presenting "
        "energy values.\n"
        "Round to 2 decimal places for power (kW), 1 decimal place for "
        "energy (kWh)."
    )
