import json

from pathlib import Path
from typing import Dict, TypedDict


class Config(TypedDict):
    file: str
    site: str
    page: str
    load: str
    next: str
    item: str
    data: Dict[str, str]


def get_config(from_file: str) -> Config:
    with open(Path(from_file).resolve(), "rb") as config:
        config = json.load(config)
        return config
