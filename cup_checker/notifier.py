"""Alert the user: console always, Telegram if configured, desktop notification on macOS/Linux/Windows."""

import html
import json
import os
import shutil
import subprocess
import sys

from cup_checker.cup_api import http_json

BOOKING_URL = "https://prenota.sanita.toscana.it"


def notify(message, telegram_html=None):
    print(message, flush=True)
    send_telegram(telegram_html or html.escape(message))
    desktop_notify(message)


# Windows PowerShell 5.1 toast; the message comes from an env var, so it is never parsed as code.
WINDOWS_TOAST = """
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
$t = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$x = $t.GetElementsByTagName('text')
$x.Item(0).AppendChild($t.CreateTextNode('CUP Toscana')) > $null
$x.Item(1).AppendChild($t.CreateTextNode($env:CUP_MESSAGE)) > $null
$app = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\\WindowsPowerShell\\v1.0\\powershell.exe'
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($app).Show([Windows.UI.Notifications.ToastNotification]::new($t))
"""


def desktop_notify(message):
    if sys.platform == "darwin":
        cmd, env = ["osascript", "-e", f"display notification {json.dumps(message)} with title \"CUP Toscana\" sound name \"Glass\""], None
    elif sys.platform == "win32":
        cmd, env = ["powershell", "-NoProfile", "-NonInteractive", "-Command", WINDOWS_TOAST], {**os.environ, "CUP_MESSAGE": message}
    elif shutil.which("notify-send"):
        cmd, env = ["notify-send", "-u", "critical", "CUP Toscana", message], None
    else:
        return  # no desktop notifier (headless Linux): console and Telegram still work
    try:
        subprocess.run(cmd, env=env, check=True, capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as e:  # a desktop failure must not hide the alert
        print(f"desktop notification error: {e}", file=sys.stderr, flush=True)


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
