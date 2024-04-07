from datetime import datetime
from enum import Enum
from string import Template


class Level(Enum):
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"


template = Template("$timestamp [url=$url, index=$index] $level - $message")


def log(level: Level, url, index, message):
    print(
        template.substitute(
            index=index,
            level=level.value,
            message=message,
            timestamp=datetime.now(),
            url=url,
        )
    )
