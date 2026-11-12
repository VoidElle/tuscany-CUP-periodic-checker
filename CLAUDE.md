# Rules

- NEVER read, print, cat, grep, copy or otherwise access the contents of `.env` (or any `.env*` file). It holds personal health data.
- Known `.env` keys (names only): `FISCAL_CODE`, `HEALTH_CARD_NUMBER`, `ELECTRONIC_PRESCRIPTION_NUMBER`, optional `CHECK_INTERVAL_SECONDS` (default 3600), `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` (Telegram alert sent only if both set; never log the token, it is in the API URL). Load them at runtime via environment variables; never log their values.
- `log*.txt` files are captured portal traffic with real patient data (name, fiscal code, address, diagnosis). Gitignored. Never commit them or copy their contents into code, tests, docs or this file.
- Never call the real portal with the real `.env` data from a Claude session: the response contains patient data. The user runs `main.py`. Probes with obviously fake data are fine.

# Project

Polls the Tuscany CUP booking portal (`prenota.sanita.toscana.it`) and alerts when an appointment becomes available for an electronic prescription. Python 3.14 (needs `compression.zstd`), stdlib only plus optional `brotli` (`requirements.txt`; `br` is advertised in Accept-Encoding only if importable), venv in `.venv`.

```
main.py                 # entry point: loop (interval ±20% jitter), check_once (2-6 s pause between the two calls)
cup_checker/config.py   # load_env: reads root .env, real env vars win
cup_checker/cup_api.py  # portal calls: PORTAL_HEADERS, decode_body (gzip/deflate/zstd/br), http_json, get_prescriptions, get_appointments
cup_checker/notifier.py # console + Telegram sendMessage (HTML + "Prenota ora" button, format approved by user) + desktop notification (macOS osascript, Linux notify-send, Windows PowerShell 5.1 toast)
tests/test_cup_api.py   # unit: response parsing, decode_body
tests/test_e2e.py       # end-to-end against a local fake portal (real HTTP, encodings, headers, notifications); fake data only
requirements.txt        # optional brotli only (NOT brotlipy: abandoned, same `brotli` module name, conflicts)
run.sh / run.bat        # launchers (.gitattributes keeps LF / CRLF)
addon/                  # Home Assistant add-on: config.yaml (options/schema), Dockerfile, run.sh (bashio options -> env vars), DOCS.md, translations
repository.yaml         # HA add-on repository manifest
.github/workflows/build.yml # builds ghcr.io/<owner>/{arch}-tuscany-cup-checker on tag push, context = repo root
.dockerignore           # keeps .env, log*.txt, .venv, .git out of the build context
```

- Run: `./run.sh` (macOS/Linux) or `run.bat` (Windows)
- Test: `.venv/bin/python -m tests.test_cup_api` and `.venv/bin/python -m tests.test_e2e` (local fake portal, fake data) (from root; plain `python tests/...` cannot import `cup_checker`)

# Portal API knowledge

Base: `https://prenota.sanita.toscana.it/sis-portalepren/sis-portale-prenotazione/sis-portale-prenotazione`

1. `GET getPrescrizioneElettronica?cf=<FISCAL_CODE>&nre=<ELECTRONIC_PRESCRIPTION_NUMBER>&numbersTeam=<HEALTH_CARD_NUMBER>`
   - Returns `response.paziente` (personal data, never log) and `response.listaPrescrizioni`.
   - Wrong data still returns HTTP 200 with `response: null` and `message.code: "999"`.
   - `idPrescrizione` / `idPrestazione` are regenerated on every call: always re-fetch before checking availability.
2. `POST getListaDisponibilitaPost`, JSON body `{"listaPrescrizioni": <from step 1>, "calcoloOrari": "ORARI_PRIMO_ORARIO", "calcoloAppuntamenti": "APP_DISP_UNO_PER_STRUTTURA", "tipo": "R"}`
   - Requires header `cf: <FISCAL_CODE>`. Without it: HTTP 400, empty body. No other cookie/header is required.
   - Availability = `response.listaAppuntamenti.appuntamento` non-empty.
   - No availability: empty `appuntamento`, `listaPrestazioniIndisponibili` filled, `esito[0].codice == "127"` ("Non è stato possibile calcolare nessun appuntamento disponibile").
   - `tipo: "R"` searches only the patient's own area (`sfogliamentoAree.attuale`). Wider search uses `"tipo": "S"` plus `"livelloSfogliamentoAree": N` (next area is in `sfogliamentoAree.successiva`). User chose NOT to extend the area.
   - Side effect (confirmed by user): when a slot is found, the search itself puts it in `statoAppuntamento: "RISERVATO"`, i.e. the portal temporarily holds it for this session. Every check that finds a slot holds it for a while, hiding it from other patients and possibly from the user's own browser. How long the hold lasts and whether a release call exists are unknown.
   - Available `appuntamento` (observed live): `dataAppuntamento` (YYYYMMDD), `oraAppuntamento` (HH:MM), `statoAppuntamento` (`RISERVATO`), `unita.descUnita` / `indirizzoUnita` / `nomeComuneUnita` / `provinciaUnita` / `telefonoUnita`. `appointment_details` turns these into display strings. Alerts list slots earliest first, max 10 in Telegram. In that response `esito[0]` is a `WRN` warning (maximum waiting time exceeded), not an error.

# HTTP / notification behavior

- `PORTAL_HEADERS` (portal calls only) mirror the portal web app's request headers, including a Chrome User-Agent and `Sec-Ch-Ua` / `Sec-Fetch-*`. These browser headers were added by the user, as the user's own decision.
- Do not put `Connection` in headers: urllib always sends `Connection: close` and overrides it.
- `Accept-Encoding` must only list encodings `decode_body` can decode (`br` only if `brotli` imports). Unknown `Content-Encoding` raises an error.
- urllib title-cases header names on the wire (`cf` arrives as `Cf`): compare header names case-insensitively in tests.
- Telegram calls get only `Content-Type: application/json`, never `PORTAL_HEADERS`.
- Errors: `notify_error` alerts on console (stderr), Telegram and desktop. The same error repeated on consecutive rounds is logged as `error (repeated)` without a new alert. The error text is capped at 500 chars. Never put patient data in exception messages.
- Startup: a stderr warning appears when `brotli` is missing.

# Home Assistant add-on

- Image base `ghcr.io/home-assistant/{arch}-base:3.22` = Alpine 3.22, Python 3.12 + `py3-brotli`. Code must stay Python 3.12 compatible: `compression.zstd` is optional (`zstd` is advertised only if it imports).
- Check 3.12 compatibility with `uv run --no-project --python 3.12 python -m tests.test_cup_api` (and `tests.test_e2e`).
- Options in `config.yaml`, `translations/*.yaml` and `run.sh` must keep the same keys. Patient fields use schema `password`. Never log option values in `run.sh`.
- No `.env` in the container: `run.sh` exports the env vars and `load_env` is a no-op. No desktop notifier exists (no `notify-send`), so alerts go to the log and Telegram only.
- Bump `version` in `addon/config.yaml` before tagging a release: the workflow tags images with that version.
