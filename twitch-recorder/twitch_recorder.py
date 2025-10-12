#!/usr/bin/env python3
import os
import subprocess
import threading
import time
from datetime import datetime
import schedule
import shutil
import json
import glob

CHANNELS = os.environ.get("CHANNELS", "")
CHANNEL_LIST = [c.strip() for c in CHANNELS.split(";") if c.strip()]

DEFAULT_POLL_INTERVAL = int(os.environ.get("DEFAULT_POLL_INTERVAL", "300"))  # seconds
SCHEDULE_WINDOWS = os.environ.get("SCHEDULE_WINDOWS", "")  # Format: Day:HH:MM-HH:MM:interval, comma-separated

QUALITY = os.environ.get("QUALITY", "best")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/data")

YTDLP_BIN = shutil.which("yt-dlp")
if YTDLP_BIN is None:
    raise RuntimeError("yt-dlp binary not found. Check installation or PATH.")

def now_str():
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

def sanitize_filename(s):
    # Keep a lightweight sanitization for channel names used in the filename
    return "".join(c for c in s if c.isalnum() or c in " -_").strip()

def build_yt_dlp_cmd(channel):
    """
    Build the yt-dlp command for recording the live Twitch stream.
    Output template: {date} {channel} {title}.{ext}  (yt-dlp will replace %(title)s and %(ext)s)
    Force merged output format to mp4 with --merge-output-format mp4.
    """
    sanitized_channel = sanitize_filename(channel) or channel
    # Put the date at the start of the filename as requested, then channel, then yt-dlp's title placeholder
    output_template = os.path.join(OUTPUT_DIR, f"{now_str()} {sanitized_channel} %(title)s.%(ext)s")
    cmd = [
        YTDLP_BIN,
        "-f",
        QUALITY,
        "-o",
        output_template,
        "--merge-output-format",
        "mp4",
        f"https://www.twitch.tv/{channel}",
    ]
    return cmd

def cleanup_intermediate_files_for_channel(channel):
    """
    Remove intermediate/partial files related to the channel in the output directory.
    This targets files with extension .part that contain the channel name in their filename.
    """
    sanitized_channel = sanitize_filename(channel) or channel
    pattern = os.path.join(OUTPUT_DIR, f"*{sanitized_channel}*")
    for path in glob.glob(pattern):
        if path.endswith(".part"):
            try:
                os.remove(path)
                print(f"[{channel}] Removed intermediate file: {path}")
            except Exception as e:
                print(f"[{channel}] Failed to remove intermediate file {path}: {e}")

def record_stream(channel):
    while True:
        try:
            print(f"[{channel}] Checking stream...")
            cmd = build_yt_dlp_cmd(channel)
            print(f"[{channel}] Running: {' '.join(cmd)}")
            # Let yt-dlp print to stdout/stderr directly
            result = subprocess.run(cmd, capture_output=False)
            if result.returncode != 0:
                print(f"[{channel}] Stream not live or error (exit code {result.returncode}), retrying in {DEFAULT_POLL_INTERVAL}s")
                time.sleep(DEFAULT_POLL_INTERVAL)
            else:
                # Successful recording finished; cleanup any leftover intermediate files for this channel
                print(f"[{channel}] Recording finished successfully. Cleaning intermediate files and continuing polling...")
                cleanup_intermediate_files_for_channel(channel)
                # continue immediately to check again
        except Exception as e:
            print(f"[{channel}] Error while recording: {e}")
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

        try:
            getattr(schedule.every(), day.lower()).at(start_time).do(job)
            print(f"Scheduled job for {day} at {start_time} for channels: {CHANNEL_LIST}")
        except Exception as e:
            print(f"Failed to schedule window '{w}': {e}")

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

