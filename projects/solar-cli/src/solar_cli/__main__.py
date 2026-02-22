import argparse
import os
import sys

import anthropic

from solar_cli.agent import ask


def main() -> None:
    parser = argparse.ArgumentParser(description="Solar CLI")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print generated Flux queries before execution",
    )
    args = parser.parse_args()

    missing = [
        var
        for var in ("INFLUX_URL", "INFLUX_TOKEN", "ANTHROPIC_API_KEY")
        if not os.environ.get(var)
    ]
    if missing:
        print(f"Missing required environment variables: {', '.join(missing)}")
        sys.exit(1)

    client = anthropic.Anthropic()
    messages: list[dict] = []

    print("Solar CLI — ask questions about your solar production. Type 'quit' to exit.")

    while True:
        try:
            user_input = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit"):
            break

        try:
            answer = ask(client, messages, user_input, verbose=args.verbose)
            print(f"\n{answer}")
        except anthropic.APIError as e:
            print(f"\nAPI error: {e}")


if __name__ == "__main__":
    main()
