# Rules

- NEVER read, print, cat, grep, copy or otherwise access the contents of `.env` (or any `.env*` file). It holds personal health data.
- Known `.env` keys (names only): `FISCAL_CODE`, `HEALTH_CARD_NUMBER`, `ELECTRONIC_PRESCRIPTION_NUMBER`, optional `CHECK_INTERVAL_SECONDS` (default 3600), `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` (Telegram alert sent only if both set; never log the token, it is in the API URL). Load them at runtime via environment variables; never log their values.
- `log*.txt` files are captured portal traffic with real patient data (name, fiscal code, address, diagnosis). Gitignored. Never commit them or copy their contents into code, tests, docs or this file.
- Never call the real portal with the real `.env` data from a Claude session: the response contains patient data. The user runs `main.py`. Probes with obviously fake data are fine.

# Project

Polls the Tuscany CUP booking portal (`prenota.sanita.toscana.it`) and alerts when an appointment becomes available for an electronic prescription. Python 3.14, stdlib only, venv in `.venv`.

```
main.py                 # entry point: loop, check_once
cup_checker/config.py   # load_env: reads root .env, real env vars win
cup_checker/cup_api.py  # portal calls
cup_checker/notifier.py # console + Telegram sendMessage (HTML + "Prenota ora" button, format approved by user) + macOS notification
tests/test_cup_api.py   # assert-based self-check
```

- Run: `.venv/bin/python main.py`
- Test: `.venv/bin/python -m tests.test_cup_api` (from root; plain `python tests/...` cannot import `cup_checker`)

# Portal API knowledge

Base: `https://prenota.sanita.toscana.it/sis-portalepren/sis-portale-prenotazione/sis-portale-prenotazione`

1. `GET getPrescrizioneElettronica?cf=<FISCAL_CODE>&nre=<ELECTRONIC_PRESCRIPTION_NUMBER>&numbersTeam=<HEALTH_CARD_NUMBER>`
   - Returns `response.paziente` (personal data, never log) and `response.listaPrescrizioni`.
   - Wrong data still returns HTTP 200 with `response: null` and `message.code: "999"`.
   - `idPrescrizione` / `idPrestazione` are regenerated on every call: always re-fetch before checking availability.
2. `POST getListaDisponibilitaPost`, JSON body `{"listaPrescrizioni": <from step 1>, "calcoloOrari": "ORARI_PRIMO_ORARIO", "calcoloAppuntamenti": "APP_DISP_UNO_PER_STRUTTURA", "tipo": "R"}`
   - Requires header `cf: <FISCAL_CODE>`. Without it: HTTP 400, empty body. No other cookie/header needed.
   - Availability = `response.listaAppuntamenti.appuntamento` non-empty.
   - No availability: empty `appuntamento`, `listaPrestazioniIndisponibili` filled, `esito[0].codice == "127"` ("Non è stato possibile calcolare nessun appuntamento disponibile").
   - `tipo: "R"` searches only the patient's own area (`sfogliamentoAree.attuale`). Wider search uses `"tipo": "S"` plus `"livelloSfogliamentoAree": N` (next area is in `sfogliamentoAree.successiva`). User chose NOT to extend the area.
   - Shape of an available `appuntamento` is unknown (never observed): the positive path is untested.
