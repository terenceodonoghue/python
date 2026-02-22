import json
import os

from influxdb_client import InfluxDBClient


def execute_query(query: str) -> str:
    """Execute a Flux query and return results as a JSON string."""
    url = os.environ["INFLUX_URL"]
    token = os.environ["INFLUX_TOKEN"]
    org = os.environ.get("INFLUX_ORG", "homelab")

    try:
        with InfluxDBClient(url=url, token=token, org=org) as client:
            tables = client.query_api().query(query)

            records = []
            for table in tables:
                for record in table.records:
                    records.append(
                        {
                            "_time": record.get_time().isoformat(),
                            "_field": record.get_field(),
                            "_value": record.get_value(),
                            "_measurement": record.get_measurement(),
                        }
                    )

            if not records:
                return json.dumps({"result": "No data found for this query."})
            return json.dumps(records, default=str)

    except Exception as e:
        return json.dumps({"error": str(e)})
