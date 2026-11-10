"""Client for the Tuscany CUP booking portal API."""

import json
import os
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = "https://prenota.sanita.toscana.it/sis-portalepren/sis-portale-prenotazione/sis-portale-prenotazione"


def http_json(url, payload=None, headers=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", "Accept": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        # Path only: the query string holds personal data.
        raise RuntimeError(f"{e.code} on {urllib.parse.urlparse(url).path.rsplit('/', 1)[-1]}: {e.read()[:300]!r}") from e


def get_prescriptions():
    query = urllib.parse.urlencode({
        "cf": os.environ["FISCAL_CODE"],
        "nre": os.environ["ELECTRONIC_PRESCRIPTION_NUMBER"],
        "numbersTeam": os.environ["HEALTH_CARD_NUMBER"],
    })
    body = http_json(f"{BASE_URL}/getPrescrizioneElettronica?{query}")
    prescriptions = body.get("response", {}).get("listaPrescrizioni")
    if not prescriptions:
        # Do not dump the body: it contains patient personal data.
        raise RuntimeError(f"Prescription not found: {body.get('response', {}).get('esito')}")
    return prescriptions


def get_appointments(prescriptions):
    body = http_json(f"{BASE_URL}/getListaDisponibilitaPost", {
        "listaPrescrizioni": prescriptions,
        "calcoloOrari": "ORARI_PRIMO_ORARIO",
        "calcoloAppuntamenti": "APP_DISP_UNO_PER_STRUTTURA",
        "tipo": "R",
    }, headers={"cf": os.environ["FISCAL_CODE"]})
    return appointments_from(body)


def appointments_from(body):
    return ((body.get("response") or {}).get("listaAppuntamenti") or {}).get("appuntamento") or []


def service_names(prescriptions):
    return [p.get("descrizionePrestazione") for rx in prescriptions.get("prescrizione") or []
            for p in (rx.get("listaPrestazioni") or {}).get("prestazione") or [] if p.get("descrizionePrestazione")]
