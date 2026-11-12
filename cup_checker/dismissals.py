"""Telegram "Non sono disponibile" button: remembers dismissed slots so the same slot is not alerted again."""

import json
import os
import re
import sys
import threading
import time
from datetime import date
from pathlib import Path

from cup_checker.cup_api import http_json

PREFIX = "skip:"
KEY_RE = re.compile(r"^\d{8}\|\d{2}:\d{2}\|[\w-]{1,30}$")  # YYYYMMDD|HH:MM|idUnita, see cup_api.slot_key
_lock = threading.Lock()


def state_file():
    # DATA_DIR=/data in the Home Assistant add-on (persists across restarts); project root otherwise.
    return Path(os.environ.get("DATA_DIR") or Path(__file__).resolve().parent.parent) / "dismissed.json"


def _load():
    try:
        keys = json.loads(state_file().read_text())
    except (OSError, ValueError):
        return set()
    today = date.today().strftime("%Y%m%d")
    return {k for k in keys if isinstance(k, str) and KEY_RE.match(k) and k[:8] >= today}  # past slots expire


def dismissed():
    with _lock:
        keys = _load()
        try:
            on_disk = json.loads(state_file().read_text())
        except (OSError, ValueError):
            on_disk = None  # missing or corrupted: rewritten below if it exists
        if state_file().exists() and on_disk != sorted(keys):
            state_file().write_text(json.dumps(sorted(keys)))  # drop past slots (or a corrupted file) from disk, called every check
        return keys


def dismiss(key):
    with _lock:
        keys = _load() | {key}
        state_file().write_text(json.dumps(sorted(keys)))


def handle_update(update, chat_id, token):
    query = update.get("callback_query") or {}
    data = query.get("data") or ""
    if not data.startswith(PREFIX):
        return
    key = data[len(PREFIX):]
    # Trust boundary: only button presses from the configured chat, with a well-formed slot key.
    from_chat = str(((query.get("message") or {}).get("chat") or {}).get("id"))
    ok = from_chat == chat_id and KEY_RE.match(key)
    if ok:
        dismiss(key)
    try:
        http_json(f"https://api.telegram.org/bot{token}/answerCallbackQuery", {
            "callback_query_id": query.get("id"),
            "text": "👍 Ok, non ti avviso più per questo posto." if ok else "Azione non valida.",
        })
    except Exception:  # the toast is cosmetic; the dismissal is already saved
        pass


def poll_forever():
    """Long-poll Telegram for button presses. Runs in a daemon thread; does nothing without Telegram config."""
    token, chat_id = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not (token and chat_id):
        return
    offset = None
    while True:
        try:
            body = http_json(f"https://api.telegram.org/bot{token}/getUpdates", {
                "timeout": 50, "allowed_updates": ["callback_query"], **({"offset": offset} if offset else {}),
            })
            for update in body.get("result") or []:
                offset = update["update_id"] + 1
                handle_update(update, chat_id, token)
        except Exception as e:  # error text never contains the token (http_json keeps only the endpoint name)
            print(f"telegram polling error: {e}", file=sys.stderr, flush=True)
            time.sleep(30)
