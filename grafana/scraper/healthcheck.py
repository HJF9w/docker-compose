#!/usr/bin/env python3
"""
Healthcheck script for Dockerfile.

Logic:
- If /tmp/last_run does not exist -> exit 1 (unhealthy).
- If CRON_SCHEDULE is set, use croniter to estimate the expected interval from the last run timestamp,
  then allow up to 3x that interval (min 60s).
- If CRON_SCHEDULE is not set, fall back to INTERVAL_SECONDS or INTERVAL_MINUTES env vars, else default 600s.
- If the last_run file mtime is older than the threshold -> exit 1, else exit 0.
"""
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

LAST_RUN = Path("/tmp/last_run")

def main():
    if not LAST_RUN.exists():
        # never run
        sys.exit(1)
    try:
        mtime = LAST_RUN.stat().st_mtime
        # Interpret the timestamp as UTC to match the entrypoint writes
        last_dt = datetime.fromtimestamp(mtime, tz=timezone.utc)
        now = datetime.now(timezone.utc)
        age = (now - last_dt).total_seconds()
    except Exception:
        sys.exit(1)

    # Default interval (seconds)
    default_interval = 600

    cron_expr = os.getenv("CRON_SCHEDULE", "").strip()
    interval = None

    if cron_expr:
        try:
            from croniter import croniter
            # Compute next scheduled run from the last run time
            itr = croniter(cron_expr, last_dt)
            next_dt = itr.get_next(datetime)
            interval = (next_dt - last_dt).total_seconds()
            if interval <= 0:
                interval = default_interval
        except Exception:
            # If cron expression invalid, fallback to defaults
            interval = None

    if interval is None:
        # Try explicit numeric env vars
        ivs = os.getenv("INTERVAL_SECONDS", "").strip()
        if ivs.isdigit():
            interval = int(ivs)
        else:
            ivm = os.getenv("INTERVAL_MINUTES", "").strip()
            if ivm.isdigit():
                interval = int(ivm) * 60
            else:
                interval = default_interval

    # threshold: tolerate up to 3x interval, but at least 60s, and at most 24h (safety)
    threshold = max(min(interval * 3, 24 * 3600), 60)

    if age > threshold:
        # too old
        sys.exit(1)
    # healthy
    sys.exit(0)

if __name__ == "__main__":
    main()

