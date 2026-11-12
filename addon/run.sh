#!/usr/bin/with-contenv bashio

export FISCAL_CODE="$(bashio::config 'fiscal_code')"
export HEALTH_CARD_NUMBER="$(bashio::config 'health_card_number')"
export ELECTRONIC_PRESCRIPTION_NUMBER="$(bashio::config 'electronic_prescription_number')"
export CHECK_INTERVAL_SECONDS="$(bashio::config 'check_interval_seconds')"

for key in fiscal_code health_card_number electronic_prescription_number; do
  bashio::config.has_value "${key}" || bashio::exit.nok "Missing required option: ${key}"
done

# Telegram is enabled only when both values are set (same rule as the .env setup)
bashio::config.has_value 'telegram_bot_token' && export TELEGRAM_BOT_TOKEN="$(bashio::config 'telegram_bot_token')"
bashio::config.has_value 'telegram_chat_id' && export TELEGRAM_CHAT_ID="$(bashio::config 'telegram_chat_id')"

# Never log option values: they are personal health data.
bashio::log.info "Starting Tuscany CUP checker (interval ${CHECK_INTERVAL_SECONDS}s, telegram $([ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_CHAT_ID:-}" ] && echo on || echo off))"
export DATA_DIR=/data   # persists dismissed slots across restarts
exec python3 -u main.py
