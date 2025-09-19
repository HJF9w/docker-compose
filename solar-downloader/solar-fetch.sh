#!/usr/bin/env bash
set -euo pipefail

# Configurable via env vars (set defaults)
URL="${URL:-https://fam-lange.de/solar.php}"
IMAGE_URL="${IMAGE_URL:-https://fam-lange.de/pic/solar.png}"
OUTPUT_DIR="${OUTPUT_DIR:-/data}"
PREFIX="${PREFIX:-}"            # optional prefix for filenames
RETRIES="${RETRIES:-2}"        # download retries
RETRY_DELAY="${RETRY_DELAY:-5}" # seconds between retries

# Locking to avoid overlap (simple mkdir lock)
LOCKDIR="/var/lock/solar-fetch.lock"
cleanup() {
  rm -rf "$LOCKDIR"
}
if mkdir "$LOCKDIR" 2>/dev/null; then
  trap cleanup EXIT
else
  echo "$(date -Is) [solar-fetch] Another run is in progress, exiting." >&2
  exit 0
fi

timestamp() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

echo "$(timestamp) [solar-fetch] Starting"

# ensure output dir exists
mkdir -p "$OUTPUT_DIR"
if [ ! -w "$OUTPUT_DIR" ]; then
  echo "$(timestamp) [solar-fetch] ERROR: output dir $OUTPUT_DIR not writable" >&2
  exit 2
fi

# fetch HTML
html=""
if ! html="$(curl -fsSL --max-time 30 "$URL")"; then
  echo "$(timestamp) [solar-fetch] WARNING: failed to fetch $URL" >&2
fi

# Parse value from HTML (keeps same sed pattern as before)
username="$(printf '%s' "$html" | sed -n "s/.*heute:&nbsp; &nbsp; <strong>  \([^<]*\).*/\1/p" | head -n1 || true)"
username="${username:-unknown}"

# === FIX: derive a filename-short from digits only ===
# Example: " 9.03"  -> digits -> "903"
#          "12.34" -> "1234"
l="$(printf '%s' "$username" | tr -cd '0-9')"
if [ -z "$l" ]; then
  l="unknown"
fi

now="$(date +'%Y-%m-%d')"

# filename with optional prefix
if [ -n "$PREFIX" ]; then
  filename="${PREFIX}_${l}_${now}.png"
else
  filename="${l}_${now}.png"
fi

outfile="${OUTPUT_DIR%/}/${filename}"

echo "$(timestamp) [solar-fetch] Parsed value='${username}' -> short='${l}' output='${outfile}'"

# Fetch image with retries using curl
i=0
success=0
while [ $i -le "$RETRIES" ]; do
  if curl -fSL --max-time 60 -o "$outfile" "$IMAGE_URL"; then
    success=1
    break
  else
    echo "$(timestamp) [solar-fetch] Attempt $((i+1)) failed to download $IMAGE_URL" >&2
    i=$((i+1))
    if [ $i -le "$RETRIES" ]; then
      sleep "$RETRY_DELAY"
    fi
  fi
done

if [ "$success" -eq 1 ]; then
  echo "$(timestamp) [solar-fetch] Download complete: $outfile"
  exit 0
else
  echo "$(timestamp) [solar-fetch] ERROR: failed to download image after $((RETRIES+1)) attempts" >&2
  exit 3
fi

