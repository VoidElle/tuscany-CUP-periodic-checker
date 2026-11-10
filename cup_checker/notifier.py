"""Alert the user: console always, desktop notification on macOS."""

import json
import subprocess
import sys


def notify(message):
    print(message, flush=True)
    if sys.platform == "darwin":
        subprocess.run(["osascript", "-e", f"display notification {json.dumps(message)} with title \"CUP Toscana\" sound name \"Glass\""])
