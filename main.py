"""Periodically check Tuscany CUP for available appointments of an electronic prescription."""

import json
import os
import random
import sys
import time
from datetime import datetime

from cup_checker import cup_api
from cup_checker.config import load_env
from cup_checker.cup_api import get_appointments, get_prescriptions, service_names
from cup_checker.notifier import notify_availability, notify_error


def check_once():
    prescriptions = get_prescriptions()
    time.sleep(random.uniform(2, 6))  # gap between the two calls, like a person reading the page
    appointments = get_appointments(prescriptions)
    stamp = datetime.now().isoformat(timespec="seconds")
    if appointments:
        notify_availability(len(appointments), service_names(prescriptions))
        print(json.dumps(appointments, indent=2, ensure_ascii=False), flush=True)
    else:
        print(f"[{stamp}] no availability", flush=True)
    return bool(appointments)


def main():
    load_env()
    if not cup_api.brotli:
        print("warning: brotli not installed, Brotli (br) responses disabled. Enable with: pip install -r requirements.txt",
              file=sys.stderr, flush=True)
    interval = int(os.environ.get("CHECK_INTERVAL_SECONDS", "3600"))
    last_error = None
    while True:
        try:
            check_once()
            last_error = None
        except Exception as e:  # keep looping on network/API errors
            if str(e) == last_error:  # same error as last round: log only, do not alert again
                print(f"[{datetime.now().isoformat(timespec='seconds')}] error (repeated): {e}", file=sys.stderr, flush=True)
            else:
                notify_error(f"[{datetime.now().isoformat(timespec='seconds')}] {e}", round(interval / 60))
            last_error = str(e)
        time.sleep(interval * random.uniform(0.8, 1.2))  # ±20% jitter: no fixed-period request pattern


if __name__ == "__main__":
    main()
