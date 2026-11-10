<div align="center">
  <h1>🩺 Tuscany CUP Periodic Checker</h1>
  <p><em>Controlla periodicamente il CUP della Regione Toscana e ti avvisa appena si libera un posto per la tua visita</em></p>
  <br>
  <img src="https://img.shields.io/badge/python-3.14-3776AB?style=flat-square&logo=python&logoColor=white" alt="python">
  <img src="https://img.shields.io/badge/dependencies-none-brightgreen?style=flat-square" alt="dependencies">
  <img src="https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey?style=flat-square" alt="platform">
  <img src="https://img.shields.io/badge/notifications-Telegram-26A5E4?style=flat-square&logo=telegram&logoColor=white" alt="telegram">
</div>

> **Disclaimer:** progetto non ufficiale e personale. Non è affiliato, approvato o supportato dalla Regione Toscana né dalle aziende sanitarie. Usa le stesse chiamate del portale [prenota.sanita.toscana.it](https://prenota.sanita.toscana.it): un controllo all'ora, come farebbe una persona.

Tuscany CUP Periodic Checker prende una **ricetta elettronica**, chiede al portale CUP le disponibilità e ti manda una notifica appena compare un appuntamento libero. Così non devi ricaricare la pagina a mano.

## Features ✨

- 🔁 **Controllo periodico**: di default ogni ora, intervallo configurabile, con variazione casuale di ±20% e una pausa di 2–6 s tra le due chiamate
- 📲 **Notifica Telegram**: messaggio formattato con pulsante **📅 Prenota ora** (opzionale)
- 🖥️ **Notifica desktop**: macOS (banner con suono), Linux (`notify-send`), Windows (toast)
- 🧾 **Ricetta sempre aggiornata**: la ricetta viene riletta a ogni controllo, perché il portale rigenera i suoi ID
- 🛡️ **Privacy**: i dati personali stanno solo in `.env` e non finiscono mai nei log
- 🪶 **Zero dipendenze**: solo libreria standard di Python

## Installation 📦

```bash
git clone <questo repository>
cd tuscany-CUP-periodic-checker
python3 -m venv .venv   # opzionale: run.sh usa python3 se il venv non c'è
```

Su Windows: `py -m venv .venv` (opzionale, `run.bat` usa `python` se il venv non c'è).

## Configuration ⚙️

Crea un file `.env` nella root del progetto:

```env
FISCAL_CODE=<codice fiscale>
HEALTH_CARD_NUMBER=<numero tessera sanitaria>
ELECTRONIC_PRESCRIPTION_NUMBER=<NRE della ricetta>

# Opzionali
CHECK_INTERVAL_SECONDS=3600
TELEGRAM_BOT_TOKEN=<token del bot>
TELEGRAM_CHAT_ID=<chat id>
```

| Chiave | Obbligatoria | Descrizione |
|---|---|---|
| `FISCAL_CODE` | ✅ | Codice fiscale dell'assistito |
| `HEALTH_CARD_NUMBER` | ✅ | Numero della tessera sanitaria |
| `ELECTRONIC_PRESCRIPTION_NUMBER` | ✅ | NRE della ricetta elettronica |
| `CHECK_INTERVAL_SECONDS` | ➖ | Secondi tra un controllo e l'altro (default `3600`) |
| `TELEGRAM_BOT_TOKEN` | ➖ | Token del bot, da [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_CHAT_ID` | ➖ | Chat a cui mandare l'avviso |

> ⚠️ `.env` contiene dati personali e sanitari. È già in `.gitignore`: non committarlo e non condividerlo.

### Telegram 📲

La notifica Telegram è **attiva solo se ci sono sia `TELEGRAM_BOT_TOKEN` sia `TELEGRAM_CHAT_ID`**. Senza queste chiavi arrivano solo l'avviso in console e la notifica desktop.

Per trovare il chat id:

1. Crea un bot con [@BotFather](https://t.me/BotFather) e copia il token in `.env`
2. Manda un messaggio qualsiasi al bot
3. Apri `https://api.telegram.org/bot<TOKEN>/getUpdates` nel browser (`bot` attaccato al token, senza `<` `>`)
4. Copia `message.chat.id` in `TELEGRAM_CHAT_ID`

Prova la notifica senza chiamare il portale:

```bash
.venv/bin/python -c "from cup_checker.config import load_env; load_env(); from cup_checker.notifier import notify; notify('test CUP checker')"
```

Su Windows sostituisci `.venv/bin/python` con `.venv\Scripts\python`.

## Usage 🚀

| Sistema | Comando |
|---|---|
| macOS / Linux | `./run.sh` |
| Windows | `run.bat` |

Lo script gira in loop finché non lo fermi con `Ctrl+C`.

| Output | Significato |
|---|---|
| `[<timestamp>] no availability` | Nessun posto libero, riprova al prossimo giro |
| Telegram + notifica desktop + elenco in console | 🎉 Posto libero: corri a prenotare |
| `error: ...` su stderr | Errore di rete o API, riprova al prossimo giro |

## How it works 🔧

```
┌─────────────┐  1. GET getPrescrizioneElettronica   ┌──────────────┐
│             │ ───────────────────────────────────▶ │              │
│  main.py    │  2. POST getListaDisponibilitaPost   │  Portale CUP │
│  (loop)     │ ───────────────────────────────────▶ │   Toscana    │
└──────┬──────┘                                      └──────────────┘
       │ posto libero?
       ▼
  📲 Telegram · 🖥️ desktop · ⌨️ console
```

1. **Lettura ricetta**: il portale restituisce la ricetta associata a codice fiscale, tessera e NRE
2. **Ricerca disponibilità**: la ricetta viene rimandata al portale, che risponde con gli appuntamenti liberi nell'area dell'assistito
3. **Avviso**: se la lista non è vuota, parte la notifica

Dettagli tecnici dell'API in [`CLAUDE.md`](CLAUDE.md).

## Project structure 🗂️

```
run.sh / run.bat         # avvio (macOS-Linux / Windows)
main.py                  # loop e singolo controllo
cup_checker/
  config.py              # lettura .env
  cup_api.py             # chiamate al portale
  notifier.py            # console + Telegram + desktop
tests/
  test_cup_api.py        # self-check
```

## Tests 🧪

```bash
.venv/bin/python -m tests.test_cup_api
```

Va lanciato dalla root con `-m`.

## Limitations ⚠️

- Cerca solo nell'**area dell'assistito**, non nelle aree limitrofe
- Il caso "appuntamento disponibile" non è ancora stato osservato dal vivo, quindi la notifica non riporta data e struttura
- Si ferma se il computer va in sospensione o se chiudi il terminale
- Su Linux senza `notify-send` (es. server headless) non c'è notifica desktop: restano console e Telegram
- Su Windows serve Windows PowerShell 5.1 (`powershell.exe`, già incluso in Windows 10/11)

## Troubleshooting 🔍

### `error: Prescription not found (portal code 999)`
Codice fiscale, tessera o NRE errati, oppure ricetta già prenotata o scaduta. Controlla i valori in `.env`. Il messaggio del portale non viene stampato, perché contiene il codice fiscale.

### `error: 400 on getListaDisponibilitaPost`
Il portale ha rifiutato la ricerca. Di solito il codice fiscale non arriva nell'header `cf`. Controlla `FISCAL_CODE` in `.env`.

### `getUpdates` risponde `{"ok":false,"error_code":404}`
Il token nell'URL è sbagliato. Scrivi `bot` attaccato al token, senza `<` `>` né spazi. Se non funziona ancora, rigenera il token con `/token` su BotFather.

### `telegram error: ...`
La notifica Telegram non è partita, ma quella desktop sì. Controlla token e chat id con il comando di test in [Telegram](#telegram-).

### `desktop notification error: ...`
La notifica desktop non è partita, ma console e Telegram sì. Su Linux installa `notify-send` (pacchetto `libnotify-bin` su Debian/Ubuntu, `libnotify` su Fedora/Arch).
