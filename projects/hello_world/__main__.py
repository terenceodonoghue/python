import os, sys


def main() -> int:
    print("Hello, world!")
    return os.EX_OK


if __name__ == "__main__":
    sys.exit(main())
