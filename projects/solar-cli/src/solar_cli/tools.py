QUERY_INFLUXDB_TOOL = {
    "name": "query_influxdb",
    "description": (
        "Execute a Flux query against the solar InfluxDB instance. "
        "Returns tabular results as a list of records, each with _time, _field, "
        "_value, and _measurement. Use this to answer questions about solar "
        "production data."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "A complete Flux query string. Must start with "
                    'from(bucket: "..."). Always filter by '
                    '_measurement == "inverter". Choose the bucket based on '
                    "the time range: solar-raw (last 30 days, 5s granularity), "
                    "solar-hourly (last 365 days, 1h aggregates), "
                    "solar-daily (all time, 1d aggregates)."
                ),
            },
        },
        "required": ["query"],
    },
}
