"""End-to-end check against a local fake portal: real HTTP, compression, headers, notifications. Fake data only."""

import gzip
import json
import os
import threading
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import main
from cup_checker import cup_api, notifier

FAKE_ENV = {"FISCAL_CODE": "AAAAAA00A00A000A", "HEALTH_CARD_NUMBER": "0", "ELECTRONIC_PRESCRIPTION_NUMBER": "0900A0000000000",
            "TELEGRAM_BOT_TOKEN": "", "TELEGRAM_CHAT_ID": ""}
PRESCRIPTIONS = {"prescrizione": [{"idPrescrizione": "1", "listaPrestazioni": {"prestazione": [{"descrizionePrestazione": "VISITA TEST "}]}}]}
ENCODERS = {"gzip": gzip.compress, "deflate": zlib.compress, "identity": lambda b: b}
if cup_api.zstd:
    ENCODERS["zstd"] = cup_api.zstd.compress
if cup_api.brotli:
    ENCODERS["br"] = cup_api.brotli.compress

state = {"encoding": "identity", "appointments": [], "found": True, "requests": []}


class FakePortal(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, status, obj):
        body = ENCODERS[state["encoding"]](json.dumps(obj).encode())
        self.send_response(status)
        if state["encoding"] != "identity":
            self.send_header("Content-Encoding", state["encoding"])
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        state["requests"].append(("GET", self.path, self.headers, None))
        if state["found"]:
            self.reply(200, {"response": {"listaPrescrizioni": PRESCRIPTIONS}, "message": {"code": "200"}})
        else:
            self.reply(200, {"response": None, "message": {"code": "999", "description": "CF AAAAAA00A00A000A errato"}})

    def do_POST(self):
        payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        state["requests"].append(("POST", self.path, self.headers, payload))
        if "cf" not in self.headers:
            self.send_response(400)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self.reply(200, {"response": {"listaAppuntamenti": {"appuntamento": state["appointments"]}}})


def run():
    os.environ.update(FAKE_ENV)
    server = ThreadingHTTPServer(("127.0.0.1", 0), FakePortal)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    cup_api.BASE_URL = f"http://127.0.0.1:{server.server_port}"
    main.time.sleep = lambda s: None  # skip the 2-6 s pause between calls

    sent = []
    notifier.send_telegram = lambda text, markup=None: sent.append(("telegram", text, markup))
    notifier.desktop_notify = lambda message: sent.append(("desktop", message))

    # 1. Every encoding is decoded; no availability sends nothing.
    for encoding in ENCODERS:
        state.update(encoding=encoding, appointments=[], requests=[])
        assert main.check_once() is False, encoding
    assert sent == [], sent
    print(f"ok encodings {sorted(ENCODERS)}")

    # 2. Request shape: portal headers, cf header, payload.
    (_, get_path, get_headers, _), (_, post_path, post_headers, payload) = state["requests"]
    assert get_path.startswith("/getPrescrizioneElettronica?cf=AAAAAA00A00A000A&nre=0900A0000000000&numbersTeam=0")
    assert post_path == "/getListaDisponibilitaPost"
    for name, value in cup_api.PORTAL_HEADERS.items():
        assert get_headers.get(name) == value and post_headers.get(name) == value, name
    assert post_headers["cf"] == FAKE_ENV["FISCAL_CODE"] and "cf" not in get_headers
    assert payload["listaPrescrizioni"] == PRESCRIPTIONS and payload["tipo"] == "R"
    print("ok request headers and payload")

    # 3. Availability: Telegram with booking button + desktop.
    state.update(encoding="gzip", appointments=[
        {"dataAppuntamento": "20261203", "oraAppuntamento": "15:30", "unita": {"descUnita": "OSPEDALE B & C", "nomeComuneUnita": "PISA"}},
        {"dataAppuntamento": "20261127", "oraAppuntamento": "09:00", "unita": {"descUnita": "AMBULATORIO A", "telefonoUnita": "000"}},
    ])
    assert main.check_once() is True
    kinds = [s[0] for s in sent]
    assert kinds == ["telegram", "desktop"], kinds
    assert "<b>2</b> appuntamenti disponibili" in sent[0][1] and "VISITA TEST" in sent[0][1]
    text = sent[0][1]
    assert text.index("27/11/2026") < text.index("03/12/2026"), "earliest slot first"
    assert "📅 <b>27/11/2026</b> ore <b>09:00</b>" in text and "☎️ 000" in text and "OSPEDALE B &amp; C" in text
    assert "27/11/2026 09:00 | AMBULATORIO A | tel. 000" in sent[1][1], sent[1][1]
    assert sent[0][2] == notifier.BOOKING_BUTTON
    print("ok availability notification")

    # 4. Prescription not found: portal description (personal data) is not in the error.
    sent.clear()
    state.update(found=False)
    try:
        main.check_once()
        raise AssertionError("expected error")
    except RuntimeError as e:
        assert "999" in str(e) and "AAAAAA00A00A000A" not in str(e), e
    state.update(found=True)
    print("ok prescription not found")

    # 5. Missing cf header: 400 with endpoint name only.
    try:
        cup_api.http_json(f"{cup_api.BASE_URL}/getListaDisponibilitaPost", {"x": 1})
        raise AssertionError("expected 400")
    except RuntimeError as e:
        assert str(e).startswith("400 on getListaDisponibilitaPost"), e
    print("ok 400 without cf")

    # 6. Telegram payload: HTML, no portal headers, button only when asked.
    calls = []
    real_http_json = notifier.http_json
    notifier.http_json = lambda url, payload=None, headers=None: calls.append((url, payload, headers))
    os.environ.update(TELEGRAM_BOT_TOKEN="123:abc", TELEGRAM_CHAT_ID="42")
    from importlib import reload
    send = reload(notifier).send_telegram  # undo the stub from above
    notifier.http_json = lambda url, payload=None, headers=None: calls.append((url, payload, headers))
    send("<b>hi</b>")
    send("<b>hi</b>", notifier.BOOKING_BUTTON)
    (url, p1, h1), (_, p2, _) = calls
    assert url == "https://api.telegram.org/bot123:abc/sendMessage" and h1 is None
    assert p1 == {"chat_id": "42", "text": "<b>hi</b>", "parse_mode": "HTML"}
    assert p2["reply_markup"] == notifier.BOOKING_BUTTON
    notifier.http_json = real_http_json
    os.environ.update(TELEGRAM_BOT_TOKEN="", TELEGRAM_CHAT_ID="")
    print("ok telegram payload")

    server.shutdown()


if __name__ == "__main__":
    run()
