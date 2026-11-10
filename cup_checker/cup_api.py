"""Client for the Tuscany CUP booking portal API."""

import gzip
import json
import os
import zlib
from compression import zstd

try:
    import brotli  # optional: pip install -r requirements.txt
except ImportError:
    brotli = None
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = "https://prenota.sanita.toscana.it/sis-portalepren/sis-portale-prenotazione/sis-portale-prenotazione"

# Same values the portal web app sends. "br" is offered only when the brotli package is installed, so every advertised encoding can be decoded.
PORTAL_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate, br, zstd" if brotli else "gzip, deflate, zstd",
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
    "Connection": "keep-alive",
    "Cookie": "cookieModale=true",
    "Origin": "https://prenota.sanita.toscana.it",
    "Referer": "https://prenota.sanita.toscana.it/",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/157.0.0.0 Safari/537.36",
    "Sec-Ch-Ua": "Chromium\";v=\"157\", \"Not-A.Brand\";v=\"99",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Dest": "empty",
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": "macOS",
}


def decode_body(raw, encoding):
    encoding = (encoding or "identity").strip().lower()
    if encoding in ("gzip", "x-gzip"):
        return gzip.decompress(raw)
    if encoding == "deflate":
        try:
            return zlib.decompress(raw)  # zlib-wrapped, per the RFC
        except zlib.error:
            return zlib.decompress(raw, -zlib.MAX_WBITS)  # raw deflate, sent by some servers
    if encoding == "zstd":
        return zstd.decompress(raw)
    if encoding == "br" and brotli:
        return brotli.decompress(raw)
    if encoding == "identity":
        return raw
    raise RuntimeError(f"unsupported Content-Encoding: {encoding}")


def http_json(url: str, payload=None, headers=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(decode_body(resp.read(), resp.headers.get("Content-Encoding")))
    except urllib.error.HTTPError as e:
        # Path only: the query string holds personal data.
        body = decode_body(e.read(), e.headers.get("Content-Encoding"))
        raise RuntimeError(f"{e.code} on {urllib.parse.urlparse(url).path.rsplit('/', 1)[-1]}: {body[:300]!r}") from e


def get_prescriptions():
    query = urllib.parse.urlencode({
        "cf": os.environ["FISCAL_CODE"],
        "nre": os.environ["ELECTRONIC_PRESCRIPTION_NUMBER"],
        "numbersTeam": os.environ["HEALTH_CARD_NUMBER"],
    })
    body = http_json(f"{BASE_URL}/getPrescrizioneElettronica?{query}", headers=PORTAL_HEADERS)
    prescriptions = (body.get("response") or {}).get("listaPrescrizioni")
    if not prescriptions:
        # Code only: response and message.description can contain patient personal data.
        raise RuntimeError(f"Prescription not found (portal code {(body.get('message') or {}).get('code')})")
    return prescriptions


def get_appointments(prescriptions):
    body = http_json(f"{BASE_URL}/getListaDisponibilitaPost", {
        "listaPrescrizioni": prescriptions,
        "calcoloOrari": "ORARI_PRIMO_ORARIO",
        "calcoloAppuntamenti": "APP_DISP_UNO_PER_STRUTTURA",
        "tipo": "R",
    }, headers={**PORTAL_HEADERS, "cf": os.environ["FISCAL_CODE"]})
    return appointments_from(body)


def appointments_from(body):
    return ((body.get("response") or {}).get("listaAppuntamenti") or {}).get("appuntamento") or []


def service_names(prescriptions):
    return [p.get("descrizionePrestazione") for rx in prescriptions.get("prescrizione") or []
            for p in (rx.get("listaPrestazioni") or {}).get("prestazione") or [] if p.get("descrizionePrestazione")]
