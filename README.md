# Tuscany CUP periodic checker

Controlla periodicamente il portale di prenotazione CUP della Regione Toscana
(`prenota.sanita.toscana.it`) e avvisa quando si libera un appuntamento per una
ricetta elettronica.

## Requisiti

- Python 3 (solo libreria standard, nessuna dipendenza)
- macOS per la notifica desktop (su altri sistemi l'avviso è solo in console)

## Configurazione

Crea un file `.env` nella root del progetto:

```
FISCAL_CODE=<codice fiscale>
HEALTH_CARD_NUMBER=<numero tessera sanitaria>
ELECTRONIC_PRESCRIPTION_NUMBER=<NRE della ricetta>
CHECK_INTERVAL_SECONDS=3600   # opzionale, default 3600 (1 ora)
```

`.env` contiene dati personali e sanitari: è in `.gitignore`, non committarlo.

## Avvio

```
./run.sh
```

Usa `.venv/bin/python` se esiste, altrimenti `python3`. Lo script gira in loop
finché non lo fermi (`Ctrl+C`).

Output:
- `[<timestamp>] no availability` se non ci sono posti
- notifica macOS con suono + elenco appuntamenti in console se ci sono posti
- `error: ...` su stderr in caso di errore di rete/API (riprova al giro dopo)

## Come funziona

1. `GET getPrescrizioneElettronica` legge la ricetta (gli ID cambiano a ogni chiamata, quindi viene riletta a ogni controllo).
2. `POST getListaDisponibilitaPost` cerca le disponibilità nell'area della paziente.

Dettagli dell'API in `CLAUDE.md`.

## Struttura

```
run.sh                  # avvio
main.py                 # loop e singolo controllo
cup_checker/config.py   # lettura .env
cup_checker/cup_api.py  # chiamate al portale
cup_checker/notifier.py # avviso console + macOS
tests/test_cup_api.py   # self-check
```

## Test

```
.venv/bin/python -m tests.test_cup_api
```

## Limiti

- Cerca solo nell'area della paziente, non nelle aree limitrofe.
- Il caso "appuntamento disponibile" non è mai stato osservato dal vivo.
- Si ferma se il Mac va in sospensione o il terminale viene chiuso.
