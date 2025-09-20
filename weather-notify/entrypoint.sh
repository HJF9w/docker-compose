#!/usr/bin/env bash
set -euo pipefail

# Entrypoint for the container.
# If CRON_EXPR is empty/unset -> run once and exit.
# Otherwise write /etc/crontabs/root with the CRON_EXPR and start crond in foreground.

CRON_EXPR="${CRON_EXPR:-}"
LOG_DIR="/logs"
CRON_LOG="/var/log/cron.log"
RUNNER="/usr/local/bin/run_weather.sh"

# Ensure log dir exists
mkdir -p "${LOG_DIR}"
touch "${CRON_LOG}" || true

# Ensure timezone is set for the container
if [ -n "${TZ:-}" ]; then
  # link tzdata file if exists
  if [ -f "/usr/share/zoneinfo/${TZ}" ]; then
    ln -sf "/usr/share/zoneinfo/${TZ}" /etc/localtime
    echo "${TZ}" > /etc/timezone || true
  fi
fi

if [ -z "${CRON_EXPR}" ]; then
  echo "CRON_EXPR is empty -> running once and exiting."
  exec "${RUNNER}"
else
  echo "Installing crontab with expression: ${CRON_EXPR}"
  # Write crontab for root (format: <cron expr> <command>)
  cat > /etc/crontabs/root <<EOF
${CRON_EXPR} ${RUNNER} >> ${CRON_LOG} 2>&1
EOF

  echo "Starting crond in foreground..."
  # -f foreground, -l log level (8 = debug/verbose). Use busybox crond present in alpine.
  exec crond -f -l 8
fi

