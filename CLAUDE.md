# Rules

- NEVER read, print, cat, grep, copy or otherwise access the contents of `.env` (or any `.env*` file). It holds personal health data.
- Known `.env` keys (names only): `FISCAL_CODE`, `HEALTH_CARD_NUMBER`, `ELECTRONIC_PRESCRIPTION_NUMBER`. Load them at runtime via environment variables; never log their values.
