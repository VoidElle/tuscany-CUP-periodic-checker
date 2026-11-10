"""Load settings from .env into the environment."""

import os
from pathlib import Path


def load_env(path=Path(__file__).resolve().parent.parent / ".env"):
    # Real environment variables win over .env values.
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))
