#!/usr/bin/env bash
set -euo pipefail

# This script converts environment variables into CLI arguments and calls the python notifier.
# Supports comma-separated LOG_FILES and IGNORE_DAYS environment variables.

PY="/usr/local/bin/weather_notifier.py"

# Build CLI args from environment variables
args=()

# Basic mappings
[ -n "${LATITUDE:-}" ] && args+=("--latitude" "${LATITUDE}")
[ -n "${LONGITUDE:-}" ] && args+=("--longitude" "${LONGITUDE}")
[ -n "${SMTP_HOST:-}" ] && args+=("--smtp-host" "${SMTP_HOST}")
[ -n "${SMTP_PORT:-}" ] && args+=("--smtp-port" "${SMTP_PORT}")
[ -n "${EMAIL_FROM:-}" ] && args+=("--email-from" "${EMAIL_FROM}")
[ -n "${EMAIL_TO:-}" ] && args+=("--email-to" "${EMAIL_TO}")
[ -n "${TIMEZONE:-}" ] && args+=("--timezone" "${TIMEZONE}")
[ -n "${EVENT_TIME:-}" ] && args+=("--event-time" "${EVENT_TIME}")
[ -n "${EVENT_TZ:-}" ] && args+=("--event-tz" "${EVENT_TZ}")

# IGNORE_DAYS: comma separated -> multiple --ignore-days flags
if [ -n "${IGNORE_DAYS:-}" ]; then
  IFS=',' read -r -a ignores <<< "${IGNORE_DAYS}"
  for ig in "${ignores[@]}"; do
    ig_trim="$(echo "${ig}" | xargs)"
    [ -n "${ig_trim}" ] && args+=("--ignore-days" "${ig_trim}")
  done
fi

# LOG_FILES: comma separated -> multiple --log-file flags
# default handled by python if not provided, but we add if provided.
if [ -n "${LOG_FILES:-}" ]; then
  IFS=',' read -r -a logs <<< "${LOG_FILES}"
  for lf in "${logs[@]}"; do
    lf_trim="$(echo "${lf}" | xargs)"
    [ -n "${lf_trim}" ] && args+=("--log-file" "${lf_trim}")
  done
fi

# Optional DEBUG mode if env var DEBUG is set to "1" or "true"
if [ "${DEBUG:-}" != "" ]; then
  case "${DEBUG}" in
    1|true|TRUE|yes|YES) args+=("--debug") ;;
  esac
fi

echo "Running: ${PY} ${args[*]}"
exec "${PY}" "${args[@]}"

