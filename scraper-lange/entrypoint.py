#!/usr/bin/env python3
"""
Entrypoint / scheduler for running scrape.py according to a cron expression (CRON_SCHEDULE).
If CRON_SCHEDULE is empty/unset, the script runs once and exits.

Mapping of environment variables to CLI flags:
  INFLUX_URL        -> --influx-url
  INFLUX_TOKEN      -> --influx-token
  INFLUX_ORG        -> --influx-org
  INFLUX_BUCKET     -> --influx-bucket
  SMTP_HOST         -> --smtp-host
  SMTP_PORT         -> --smtp-port
  SMTP_USE_TLS      -> --smtp-use-tls  (if "true" or "1")
  SMTP_USER         -> --smtp-user
  SMTP_PASS         -> --smtp-pass
  EMAIL_FROM        -> --email-from
  EMAIL_TO          -> --email-to
  POSTGRES_HOST     -> --postgres-host
  POSTGRES_PORT     -> --postgres-port
  POSTGRES_DB       -> --postgres-db
  POSTGRES_USER     -> --postgres-user
  POSTGRES_PASSWORD -> --postgres-password
  DWD_MODE          -> --dwd-mode ("off", "high-frequency", "daily", or "all")

Optional:
  TZ                -> If set, container will respect timezone (tzdata installed in image)
  CRON_SCHEDULE     -> Cron expression to schedule repeated runs (uses croniter)
                      Example: "*/10 * * * *" for every 10 minutes
  If CRON_SCHEDULE is unset or empty, runs one time and exits.
"""
import os
import shlex
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from croniter import croniter

APP_PY = "/app/scrape.py"
LAST_RUN = "/tmp/last_run"

# Build cli args from environment variables
def build_args_from_env():
    env = os.environ
    args = [sys.executable, APP_PY]
    mapping = [
        ("INFLUX_URL", "--influx-url"),
        ("INFLUX_TOKEN", "--influx-token"),
        ("INFLUX_ORG", "--influx-org"),
        ("INFLUX_BUCKET", "--influx-bucket"),
        ("SMTP_HOST", "--smtp-host"),
        ("SMTP_PORT", "--smtp-port"),
        ("SMTP_USER", "--smtp-user"),
        ("SMTP_PASS", "--smtp-pass"),
        ("EMAIL_FROM", "--email-from"),
        ("EMAIL_TO", "--email-to"),
        ("NEON_EXT_SENSOR_URL", "--neon-ext-sensor-url"),
        ("NEON_CPU_SENSOR_URL", "--neon-cpu-sensor-url"),
        ("DWD_STATION_ID", "--dwd-station-id"),
        ("DWD_MODE", "--dwd-mode"),
        ("POSTGRES_HOST", "--postgres-host"),
        ("POSTGRES_PORT", "--postgres-port"),
        ("POSTGRES_DB", "--postgres-db"),
        ("POSTGRES_USER", "--postgres-user"),
        ("POSTGRES_PASSWORD", "--postgres-password"),
    ]
    for envk, flag in mapping:
        v = env.get(envk)
        if v:
            args.extend([flag, v])

    # boolean flag SMTP_USE_TLS
    stls = env.get("SMTP_USE_TLS", "")
    if stls.lower() in ("1", "true", "yes", "on"):
        args.append("--smtp-use-tls")

    return args

def touch_last_run():
    try:
        # Use timezone-aware UTC timestamp to avoid deprecation warnings
        ts = datetime.now(timezone.utc).isoformat()
        with open(LAST_RUN, "w") as f:
            f.write(ts + "Z\n")
    except Exception as e:
        print("Warning: could not write last_run file:", e, file=sys.stderr)

# Run a single invocation, returns subprocess returncode
def run_once(args):
    now_str = datetime.now(timezone.utc).isoformat()
    print(f"[{now_str}] Running: {' '.join(shlex.quote(a) for a in args)}")
    try:
        rc = subprocess.run(args, stdout=sys.stdout, stderr=sys.stderr)
        if rc.returncode == 0:
            touch_last_run()
        else:
            print(f"Script exited with code {rc.returncode}", file=sys.stderr)
        return rc.returncode
    except Exception as e:
        print("Execution failed:", e, file=sys.stderr)
        return 2

# Scheduler using croniter
stop_requested = False

def _signal_handler(signum, frame):
    global stop_requested
    print(f"Received signal {signum}, stopping after current run...")
    stop_requested = True

signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)

def schedule_loop(cron_expr, args):
    # compute next occurrence and loop
    base = datetime.now()
    try:
        itr = croniter(cron_expr, base)
    except Exception as e:
        print("Invalid CRON_SCHEDULE:", e, file=sys.stderr)
        return 2

    while not stop_requested:
        next_run = itr.get_next(datetime)
        now = datetime.now()
        wait_seconds = (next_run - now).total_seconds()
        if wait_seconds > 0:
            # Sleep in small chunks so we can be responsive to signals
            slept = 0.0
            while slept < wait_seconds and not stop_requested:
                to_sleep = min(1.0, wait_seconds - slept)
                time.sleep(to_sleep)
                slept += to_sleep
        if stop_requested:
            break
        rc = run_once(args)
        # continue to next cron occurrence
    print("Scheduler exiting")
    return 0

def main():
    # allow TZ to be set in container env; Python uses tzinfo only where needed in script
    cron_expr = os.getenv("CRON_SCHEDULE", "").strip()
    args = build_args_from_env()

    # Validate that APP_PY exists
    if not os.path.exists(APP_PY):
        print(f"Error: {APP_PY} not found in container", file=sys.stderr)
        sys.exit(2)

    # If CRON_SCHEDULE unset/empty -> run once and exit
    if not cron_expr:
        rc = run_once(args)
        sys.exit(rc or 0)

    # Otherwise run scheduled loop
    rc = schedule_loop(cron_expr, args)
    sys.exit(rc or 0)

if __name__ == "__main__":
    main()

