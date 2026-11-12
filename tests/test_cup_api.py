from cup_checker.cup_api import appointments_from

# Shape of a real "no availability" response (esito 127).
assert appointments_from({"response": {"listaAppuntamenti": {"appuntamento": []}, "esito": [{"codice": "127"}]}}) == []
assert appointments_from({"response": {"listaAppuntamenti": None}}) == []
assert appointments_from({"response": {"listaAppuntamenti": {"appuntamento": [{"id": 1}]}}}) == [{"id": 1}]
print("ok")

from cup_checker.cup_api import service_names

assert service_names({"prescrizione": [{"listaPrestazioni": {"prestazione": [{"descrizionePrestazione": "VISITA X"}, {}]}}]}) == ["VISITA X"]
assert service_names({"prescrizione": [{"listaPrestazioni": None}]}) == []
print("ok services")

import gzip
import zlib
from cup_checker.cup_api import decode_body

body = b'{"ok": true}'
for raw, enc in [(body, None), (body, "identity"), (gzip.compress(body), "gzip"), (zlib.compress(body), "deflate"),
                 (zlib.compress(body)[2:-4], "deflate")]:
    assert decode_body(raw, enc) == body, enc
import cup_checker.cup_api as cup_api

if cup_api.zstd:
    assert decode_body(cup_api.zstd.compress(body), "zstd") == body
    assert "zstd" in cup_api.PORTAL_HEADERS["Accept-Encoding"]
else:  # Python < 3.14: zstd is neither advertised nor decoded
    assert "zstd" not in cup_api.PORTAL_HEADERS["Accept-Encoding"]

if cup_api.brotli:
    assert decode_body(cup_api.brotli.compress(body), "br") == body
    assert "br" in cup_api.PORTAL_HEADERS["Accept-Encoding"]
else:  # without the package, br is neither advertised nor decoded
    assert "br" not in cup_api.PORTAL_HEADERS["Accept-Encoding"]
try:
    decode_body(body, "compress")
    raise AssertionError("unknown encoding must be rejected")
except RuntimeError:
    pass
print("ok decode")

from cup_checker.cup_api import appointment_details

# Shape of a real available appointment (public facility data only, no patient data).
real = {"dataAppuntamento": "20261127", "oraAppuntamento": "09:00", "unita": {
    "descUnita": "106 Livornese Villa Tirrena - CARDIOLOGIA", "indirizzoUnita": "VIA MONTEBELLO,102",
    "nomeComuneUnita": "LIVORNO", "provinciaUnita": "LI", "telefonoUnita": "0586 263111"}}
assert appointment_details(real) == {"date": "27/11/2026", "time": "09:00", "facility": "106 Livornese Villa Tirrena - CARDIOLOGIA",
                                     "address": "VIA MONTEBELLO,102, LIVORNO (LI)", "phone": "0586 263111"}
assert appointment_details({"unita": None}) == {"date": "", "time": "", "facility": "", "address": "", "phone": ""}

from cup_checker.cup_api import slot_key

assert slot_key({**real, "unita": {**real["unita"], "idUnita": "658053"}}) == "20261127|09:00|658053"
assert slot_key(real) is None  # no idUnita: not dismissable
print("ok appointment details")

from datetime import datetime

from main import NIGHT_JITTER, next_sleep

for _ in range(200):
    # Daytime, 1 h interval: regular jittered interval wins.
    assert 2880 <= next_sleep(datetime(2026, 11, 12, 15, 0), 3600) <= 4320
    # 23:30: the 00:10 night check comes before the regular one.
    assert 40 * 60 - NIGHT_JITTER <= next_sleep(datetime(2026, 11, 12, 23, 30), 3600) <= 40 * 60 + NIGHT_JITTER
    # Right after the 00:10 check (ran early at 00:09): next is 00:45, not 00:10 again.
    assert 36 * 60 - NIGHT_JITTER <= next_sleep(datetime(2026, 11, 13, 0, 9), 3600) <= 36 * 60 + NIGHT_JITTER
    # After 00:45 (ran late at 00:46): no more night checks until tomorrow, regular interval.
    assert 2880 <= next_sleep(datetime(2026, 11, 13, 0, 46), 3600) <= 4320
print("ok night schedule")

import json
import os
import tempfile

from cup_checker import dismissals, notifier

with tempfile.TemporaryDirectory() as tmp:
    os.environ["DATA_DIR"] = tmp
    toasts = []
    dismissals.http_json = lambda url, payload=None, headers=None: toasts.append(payload["text"])
    press = lambda chat, data: {"update_id": 1, "callback_query": {"id": "q", "data": data, "message": {"chat": {"id": chat}}}}

    dismissals.handle_update(press(42, "skip:20991231|09:00|658053"), "42", "t")
    assert dismissals.dismissed() == {"20991231|09:00|658053"} and toasts[-1].startswith("👍")
    dismissals.handle_update(press(99, "skip:20991231|10:00|658053"), "42", "t")  # other chat: ignored
    dismissals.handle_update(press(42, "skip:../../etc"), "42", "t")  # malformed key: ignored
    assert dismissals.dismissed() == {"20991231|09:00|658053"} and toasts[-1] == "Azione non valida."
    with open(os.path.join(tmp, "dismissed.json"), "w") as f:
        json.dump(["20000101|09:00|1", "20991231|09:00|658053"], f)
    assert dismissals.dismissed() == {"20991231|09:00|658053"}, "past slots expire"
    with open(os.path.join(tmp, "dismissed.json")) as f:
        assert json.load(f) == ["20991231|09:00|658053"], "past slots are removed from the file too"
    with open(os.path.join(tmp, "dismissed.json"), "w") as f:
        f.write("not json")
    assert dismissals.dismissed() == set(), "corrupted file must not break the check"
    with open(os.path.join(tmp, "dismissed.json")) as f:
        assert json.load(f) == []
    dismissals.dismiss("20991231|09:00|658053")

    sent = []
    notifier.send_telegram = lambda text, markup=None: sent.append(markup)
    notifier.desktop_notify = lambda m: None
    slot = {"dataAppuntamento": "20991231", "oraAppuntamento": "09:00", "unita": {"idUnita": "658053", "descUnita": "X"}}
    notifier.notify_availability([slot], [])
    rows = sent[-1]["inline_keyboard"]
    assert rows[0] == [{"text": "🙅 Non sono disponibile", "callback_data": "skip:20991231|09:00|658053"}]
    assert rows[-1] == notifier.BOOKING_BUTTON["inline_keyboard"][0]
    assert len(rows[0][0]["callback_data"].encode()) <= 64  # Telegram callback_data limit
    del os.environ["DATA_DIR"]
print("ok dismissals")
