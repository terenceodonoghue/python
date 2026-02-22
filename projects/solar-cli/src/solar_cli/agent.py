import random
import sys
import threading

import anthropic

from solar_cli.influxdb import execute_query
from solar_cli.prompts import system_prompt
from solar_cli.tools import QUERY_INFLUXDB_TOOL

MAX_TOOL_CALLS = 5

_SPINNER_PHRASES = [
    "Absorbing photons",
    "Tracking the sun",
    "Charging capacitors",
    "Harvesting sunlight",
    "Warming up panels",
    "Catching rays",
    "Soaking up sunshine",
    "Calibrating inverter",
    "Reading the sky",
    "Chasing daylight",
    "Counting electrons",
    "Tilting panels",
]


class _Spinner:
    def __enter__(self):
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *_):
        self._stop.set()
        self._thread.join()
        sys.stderr.write("\r\033[K")
        sys.stderr.flush()

    def _spin(self):
        phrases = random.sample(_SPINNER_PHRASES, len(_SPINNER_PHRASES))
        idx = 0
        while not self._stop.wait(timeout=1.5):
            sys.stderr.write(f"\r\033[K\033[33m{phrases[idx % len(phrases)]}...\033[0m")
            sys.stderr.flush()
            idx += 1


def ask(
    client: anthropic.Anthropic,
    messages: list[dict],
    user_input: str,
    *,
    verbose: bool = False,
) -> str:
    """Run one question through the agent loop, returning the text answer.

    Mutates *messages* in place so conversation history is preserved across
    calls.
    """
    messages.append({"role": "user", "content": user_input})

    tool_calls = 0
    while True:
        with _Spinner():
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=system_prompt(),
                tools=[QUERY_INFLUXDB_TOOL],
                messages=messages,
            )

        messages.append({"role": "assistant", "content": response.content})

        tool_use_blocks = [
            block for block in response.content if block.type == "tool_use"
        ]

        if not tool_use_blocks:
            return "".join(
                block.text for block in response.content if block.type == "text"
            )

        tool_results = []
        for block in tool_use_blocks:
            tool_calls += 1
            if tool_calls > MAX_TOOL_CALLS:
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": '{"error": "Too many tool calls for this '
                        'question. Please summarise what you have so far."}',
                    }
                )
                continue

            flux_query = block.input["query"]
            if verbose:
                print(f"\n[Flux] {flux_query}")

            result = execute_query(flux_query)
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                }
            )

        messages.append({"role": "user", "content": tool_results})
