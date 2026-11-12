"""Periodically check Tuscany CUP for available appointments of an electronic prescription."""

import os
import random
import sys
import threading
import time
from datetime import datetime, timedelta

from cup_checker import cup_api, dismissals
from cup_checker.config import load_env
from cup_checker.cup_api import get_appointments, get_prescriptions, service_names, slot_key
from cup_checker.notifier import notify_availability, notify_error


def check_once():
    prescriptions = get_prescriptions()
    time.sleep(random.uniform(2, 6))  # gap between the two calls, like a person reading the page
    appointments = get_appointments(prescriptions)
    stamp = datetime.now().isoformat(timespec="seconds")
    skipped = dismissals.dismissed()
    fresh = [a for a in appointments if slot_key(a) not in skipped]
    if fresh:
        notify_availability(fresh, service_names(prescriptions))
    elif appointments:
        print(f"[{stamp}] {len(appointments)} slot(s) available, all marked 'non sono disponibile': no alert", flush=True)
    else:
        print(f"[{stamp}] no availability", flush=True)
    return bool(appointments)


# The portal publishes new dates around midnight: extra checks at these local times, ± NIGHT_JITTER seconds.
NIGHT_CHECKS = ((0, 10), (0, 45))
NIGHT_JITTER = 600


def next_sleep(now, interval):
    """Seconds until the next check: the regular jittered interval, or the next night check if it comes first."""
    regular = interval * random.uniform(0.8, 1.2)  # ±20% jitter: no fixed-period request pattern
    slots = [now.replace(hour=h, minute=m, second=0, microsecond=0) + timedelta(days=d) for h, m in NIGHT_CHECKS for d in (0, 1)]
    # Skip a slot we are already inside the jitter window of: that check has just run.
    upcoming = min(t for t in slots if (t - now).total_seconds() > NIGHT_JITTER)
    night = (upcoming - now).total_seconds() + random.uniform(-NIGHT_JITTER, NIGHT_JITTER)
    return min(regular, night)


def main():
    load_env()
    if not cup_api.brotli:
        print("warning: brotli not installed, Brotli (br) responses disabled. Enable with: pip install -r requirements.txt",
              file=sys.stderr, flush=True)
    interval = int(os.environ.get("CHECK_INTERVAL_SECONDS", "3600"))
    threading.Thread(target=dismissals.poll_forever, daemon=True).start()
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
        time.sleep(next_sleep(datetime.now(), interval))


if __name__ == "__main__":
    main()
