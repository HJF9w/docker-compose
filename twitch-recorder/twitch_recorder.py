#!/usr/bin/env python3
import os
import subprocess
import threading
import time
from datetime import datetime
import schedule
import shutil
import json

CHANNELS = os.environ.get("CHANNELS", "")
CHANNEL_LIST = [c.strip() for c in CHANNELS.split(";") if c.strip()]

DEFAULT_POLL_INTERVAL = int(os.environ.get("DEFAULT_POLL_INTERVAL", "300"))  # seconds
SCHEDULE_WINDOWS = os.environ.get("SCHEDULE_WINDOWS", "")  # Format: Day:HH:MM-HH:MM:interval, comma-separated

QUALITY = os.environ.get("QUALITY", "best")
DISABLE_ADS = os.environ.get("DISABLE_ADS", "true").lower() == "true"
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/data")

STREAMLINK_BIN = shutil.which("streamlink")
if STREAMLINK_BIN is None:
    raise RuntimeError("streamlink binary not found. Check installation or PATH.")

def now_str():
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

def get_stream_title(channel):
    try:
        result = subprocess.run(
            [STREAMLINK_BIN, "--json", f"https://www.twitch.tv/{channel}"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return ""
        data = json.loads(result.stdout)
        return data.get("title", "")
    except Exception:
        return ""

def sanitize_filename(s):
    return "".join(c for c in s if c.isalnum() or c in " -_").strip()

def build_streamlink_cmd(channel):
    title = get_stream_title(channel) or "untitled"
    title = sanitize_filename(title)
    filename = os.path.join(OUTPUT_DIR, f"{now_str()} {channel} {title}.ts")
    cmd = [
        STREAMLINK_BIN,
        f"https://www.twitch.tv/{channel}",
        QUALITY,
    ]
    if DISABLE_ADS:
        cmd.append("--twitch-disable-ads")
    cmd += ["-o", filename]
    return cmd

def record_stream(channel):
    while True:
        try:
            print(f"[{channel}] Checking stream...")
            cmd = build_streamlink_cmd(channel)
            result = subprocess.run(cmd, capture_output=False)
            if result.returncode != 0:
                print(f"[{channel}] Stream not live or error, retrying in {DEFAULT_POLL_INTERVAL}s")
                time.sleep(DEFAULT_POLL_INTERVAL)
            else:
                print(f"[{channel}] Recording finished, continuing polling...")
        except Exception as e:
            print(f"[{channel}] Error: {e}")
            time.sleep(DEFAULT_POLL_INTERVAL)

def start_channel_thread(channel):
    t = threading.Thread(target=record_stream, args=(channel,), daemon=True)
    t.start()
    return t

def parse_schedule_window(window_str):
    """
    Format: Day:HH:MM-HH:MM:interval
    Example: Saturday:00:00-10:00:60
    """
    try:
        day, rest = window_str.split(":", 1)
        time_range, interval = rest.rsplit(":", 1)
        start_time, end_time = time_range.split("-")
        interval = int(interval)
        return day, start_time, end_time, interval
    except Exception as e:
        print(f"Invalid schedule window '{window_str}': {e}")
        return None

def schedule_jobs():
    if not SCHEDULE_WINDOWS:
        return
    for w in SCHEDULE_WINDOWS.split(","):
        parsed = parse_schedule_window(w)
        if not parsed:
            continue
        day, start_time, end_time, interval = parsed

        def job(channel_list=CHANNEL_LIST, interval=interval):
            for ch in channel_list:
                t = threading.Thread(target=record_stream, args=(ch,), daemon=True)
                t.start()

        getattr(schedule.every(), day.lower()).at(start_time).do(job)

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Start threads for each channel
    threads = [start_channel_thread(ch) for ch in CHANNEL_LIST]

    # Schedule windows
    schedule_jobs()

    while True:
        schedule.run_pending()
        time.sleep(10)

if __name__ == "__main__":
    main()

