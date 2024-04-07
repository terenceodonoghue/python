import sys

from driver import Driver


def main() -> int:
    driver = Driver(from_file=sys.argv[1])
    return driver.run()


if __name__ == "__main__":
    sys.exit(main())
