"""Alert the user: console always, Telegram if configured, desktop notification on macOS/Linux/Windows."""

import html
import json
import os
import shutil
import subprocess
import sys

from cup_checker.cup_api import appointment_details, http_json, slot_key
from cup_checker.dismissals import PREFIX as DISMISS_PREFIX

BOOKING_URL = "https://prenota.sanita.toscana.it"


BOOKING_BUTTON = {"inline_keyboard": [[{"text": "📅 Prenota ora", "url": BOOKING_URL}]]}


def notify(message, telegram_html=None, reply_markup=None, stream=sys.stdout):
    print(message, file=stream, flush=True)
    send_telegram(telegram_html or html.escape(message), reply_markup)
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


MAX_LISTED = 10  # keeps the Telegram message well under its 4096-char limit


def notify_availability(appointments, services):
    count = len(appointments)
    details = sorted(({**appointment_details(a), "key": slot_key(a)} for a in appointments), key=lambda d: (d["date"][6:], d["date"][3:5], d["date"][:2], d["time"]))
    shown, hidden = details[:MAX_LISTED], count - min(count, MAX_LISTED)

    plain = [f"{count} appointment(s) available! Book at {BOOKING_URL}"]
    plain += [" | ".join(x for x in (f"{d['date']} {d['time']}".strip(), d["facility"], d["address"], d["phone"] and f"tel. {d['phone']}") if x)
              for d in details]

    lines = [
        "🩺 <b>CUP Toscana: posto libero!</b>",
        "",
        f"✅ <b>{count}</b> {'appuntamento disponibile' if count == 1 else 'appuntamenti disponibili'}",
        *(f"🏥 {html.escape(s.strip())}" for s in services),
    ]
    for d in shown:
        lines.append("")
        lines.append(f"📅 <b>{html.escape(d['date'])}</b> ore <b>{html.escape(d['time'])}</b>" if d["time"] else f"📅 <b>{html.escape(d['date'])}</b>")
        lines += [f"{icon} {html.escape(d[key])}" for icon, key in (("🏢", "facility"), ("📍", "address"), ("☎️", "phone")) if d[key]]
    if hidden:
        lines += ["", f"➕ <i>altri {hidden} sul portale</i>"]
    lines += ["", "⏳ <i>I posti vanno via in fretta: prenota subito.</i>"]
    dismiss_rows = [[{"text": "🙅 Non sono disponibile" if len(shown) == 1 else f"🙅 Non disponibile {d['date']} {d['time']}".strip(),
                      "callback_data": DISMISS_PREFIX + d["key"]}] for d in shown if d["key"]]
    notify("\n".join(plain), "\n".join(lines), {"inline_keyboard": dismiss_rows + BOOKING_BUTTON["inline_keyboard"]})


def notify_error(error, retry_minutes):
    text = str(error)[:500]  # cap: Telegram limit is 4096 chars, and a short line reads better
    lines = [
        "⚠️ <b>CUP Toscana: errore durante il controllo</b>",
        "",
        f"<code>{html.escape(text)}</code>",
        "",
        f"🔁 <i>Riprovo tra circa {retry_minutes} minuti.</i>",
    ]
    notify(f"error: {text}", "\n".join(lines), stream=sys.stderr)


def send_telegram(text_html, reply_markup=None):
    token, chat_id = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not (token and chat_id):
        return
    try:
        http_json(f"https://api.telegram.org/bot{token}/sendMessage", {
            "chat_id": chat_id,
            "text": text_html,
            "parse_mode": "HTML",
            **({"reply_markup": reply_markup} if reply_markup else {}),
        })
    except Exception as e:  # a Telegram failure must not hide the alert; error text never contains the token
        print(f"telegram error: {e}", file=sys.stderr, flush=True)
