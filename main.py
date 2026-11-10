"""Periodically check Tuscany CUP for available appointments of an electronic prescription."""

import json
import os
import sys
import time
from datetime import datetime

from cup_checker.config import load_env
from cup_checker.cup_api import get_appointments, get_prescriptions
from cup_checker.notifier import notify


def check_once():
    appointments = get_appointments(get_prescriptions())
    stamp = datetime.now().isoformat(timespec="seconds")
    if appointments:
        notify(f"{len(appointments)} appointment(s) available! Book at https://prenota.sanita.toscana.it")
        print(json.dumps(appointments, indent=2, ensure_ascii=False), flush=True)
    else:
        print(f"[{stamp}] no availability", flush=True)
    return bool(appointments)


def main():
    load_env()
    interval = int(os.environ.get("CHECK_INTERVAL_SECONDS", "3600"))
    while True:
        try:
            check_once()
        except Exception as e:  # keep looping on network/API errors
            print(f"[{datetime.now().isoformat(timespec='seconds')}] error: {e}", file=sys.stderr, flush=True)
        time.sleep(interval)


if __name__ == "__main__":
    main()
