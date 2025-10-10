#!/bin/sh
# entrypoint.sh - ensure data directory exists and then exec the command
set -e

# create data directory if missing
if [ ! -d "/app/data" ]; then
  mkdir -p /app/data
fi
if [ ! -d "/app/thumbs" ]; then
  mkdir -p /app/thumbs
fi

# ensure permissions are reasonable
chmod -R 755 /app/data /app/thumbs

# If the container was started with a mounted data directory owned by root,
# the app will still be able to read it. Exec the passed command.
exec "$@"

