# Tuscany CUP Checker

Checks the Tuscany CUP booking portal (`prenota.sanita.toscana.it`) for an electronic prescription and alerts you as soon as an appointment slot frees up. By default it checks once an hour.

> Unofficial project. Not affiliated with, endorsed by or supported by Regione Toscana or the local health authorities.

## Setup

1. Fill in **Fiscal code**, **Health card number** and **Electronic prescription number (NRE)**.
2. Optional: set **Telegram bot token** and **Telegram chat id** to get alerts on Telegram (see the project README for how to find the chat id).
3. Start the add-on and open the **Log** tab.

The three patient fields are personal health data. They are stored by Home Assistant in the add-on options, masked in the UI, and never written to the log.

## Options

| Option | Default | Meaning |
|--------|---------|---------|
| `fiscal_code` | *(required)* | Codice fiscale of the patient |
| `health_card_number` | *(required)* | Tessera sanitaria number |
| `electronic_prescription_number` | *(required)* | NRE of the prescription |
| `check_interval_seconds` | `3600` | Seconds between checks (300–86400), randomised by ±20%. Two extra checks also run at 00:10 and 00:45 (±10 min, Home Assistant time zone), when the portal publishes new dates |
| `telegram_bot_token` | *(empty)* | Bot token from @BotFather |
| `telegram_chat_id` | *(empty)* | Chat that receives the alerts |

Telegram is enabled only when both Telegram options are set.

## Alerts

- **Slot available**: Telegram message with date, time, facility, address and phone of each slot (earliest first, up to 10) and a **📅 Prenota ora** button. The log gets one line per slot.
- **🙅 Non sono disponibile**: button under each slot in the Telegram message. A dismissed slot is never alerted again; the choice is kept in the add-on data across restarts.
- **Error** (network, portal, wrong data): Telegram message and log line. The same error repeated on the next round is logged only, without a new alert.
- Without Telegram, alerts appear only in the add-on log: there is no desktop notification inside Home Assistant.

## Log messages

| Line | Meaning |
|---|---|
| `[<timestamp>] no availability` | No free slot, next check at the next round |
| `error: Prescription not found (portal code 999)` | Wrong fiscal code, card number or NRE, or the prescription is already booked or expired |
| `error: 400 on getListaDisponibilitaPost` | The portal rejected the availability search |

## Limitations

- Searches only the patient's own area.
- Zstandard (`zstd`) responses are not supported in this image (Python 3.12). gzip, deflate and Brotli are.
