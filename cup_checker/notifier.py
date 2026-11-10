"""Alert the user: console always, Telegram if configured, desktop notification on macOS."""

import html
import json
import os
import subprocess
import sys

from cup_checker.cup_api import http_json

BOOKING_URL = "https://prenota.sanita.toscana.it"


def notify(message, telegram_html=None):
    print(message, flush=True)
    send_telegram(telegram_html or html.escape(message))
    if sys.platform == "darwin":
        subprocess.run(["osascript", "-e", f"display notification {json.dumps(message)} with title \"CUP Toscana\" sound name \"Glass\""])


def notify_availability(count, services):
    plain = f"{count} appointment(s) available! Book at {BOOKING_URL}"
    lines = [
        "🩺 <b>CUP Toscana: posto libero!</b>",
        "",
        f"✅ <b>{count}</b> {'appuntamento disponibile' if count == 1 else 'appuntamenti disponibili'}",
        *(f"🏥 {html.escape(s.strip())}" for s in services),
        "",
        "⏳ <i>I posti vanno via in fretta: prenota subito.</i>",
    ]
    notify(plain, "\n".join(lines))


def send_telegram(text_html):
    token, chat_id = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not (token and chat_id):
        return
    try:
        http_json(f"https://api.telegram.org/bot{token}/sendMessage", {
            "chat_id": chat_id,
            "text": text_html,
            "parse_mode": "HTML",
            "reply_markup": {"inline_keyboard": [[{"text": "📅 Prenota ora", "url": BOOKING_URL}]]},
        })
    except Exception as e:  # a Telegram failure must not hide the alert; error text never contains the token
        print(f"telegram error: {e}", file=sys.stderr, flush=True)
