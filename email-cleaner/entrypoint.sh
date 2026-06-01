#!/bin/sh
set -eu

: "${CRON_SCHEDULE:=4 1 * * *}"
SCRIPT_PATH="/usr/local/bin/del_mail.py"

# Find Python interpreter
PYTHON_BIN="$(command -v python3 2>/dev/null || command -v python 2>/dev/null || echo /usr/local/bin/python3)"
if [ ! -x "$PYTHON_BIN" ]; then
  echo "ERROR: Could not find Python at ${PYTHON_BIN}" >&2
  exit 1
fi

# Write crontab
cat > /etc/crontabs/root <<EOF
MAILTO=""
SHELL=/bin/sh
PATH=/usr/local/bin:/usr/bin:/bin
EOF

# Export del_mail_script_* env variables
env | grep -E '^del_mail_script_' | while IFS='=' read -r k v; do
  printf '%s="%s"\n' "$k" "$v" >> /etc/crontabs/root
done

# Append cron schedule: output goes to stdout/stderr for Docker logs
printf '%s %s %s\n' "${CRON_SCHEDULE}" "${PYTHON_BIN}" "${SCRIPT_PATH}" >> /etc/crontabs/root

# Show crontab for debugging
echo "==== /etc/crontabs/root ===="
cat /etc/crontabs/root
echo "============================"
echo "Using python: ${PYTHON_BIN}"

# Start cron in foreground
CROND_ARGS="-f"
if [ "${DEBUG_CRON:-0}" != "0" ]; then
  CROND_ARGS="${CROND_ARGS} -x ext"
fi

exec crond $CROND_ARGS

