import glob
import json
import os
import time

import requests


VIDEO_DIR = os.getenv("TELEGRAM_VIDEO_DIR", "/data/videos")
VIDEO_GLOB = os.getenv("TELEGRAM_VIDEO_GLOB", "*_timelapse.mp4")
STATE_FILE = os.getenv("TELEGRAM_STATE_FILE", "/data/videos/.telegram_sent.json")
POLL_INTERVAL = int(os.getenv("TELEGRAM_POLL_INTERVAL", "30"))
SETTLED_SECONDS = int(os.getenv("TELEGRAM_SETTLED_SECONDS", "30"))
REQUEST_TIMEOUT = int(os.getenv("TELEGRAM_REQUEST_TIMEOUT", "300"))
API_BASE = os.getenv("TELEGRAM_API_BASE", "https://api.telegram.org")


def load_state():
    try:
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as e:
        print(f"Could not read state file {STATE_FILE}: {e}", flush=True)
        return {}


def save_state(state):
    tmp_file = f"{STATE_FILE}.tmp"
    with open(tmp_file, "w") as f:
        json.dump(state, f, sort_keys=True)
    os.replace(tmp_file, STATE_FILE)


def file_signature(path):
    stat = os.stat(path)
    return f"{stat.st_size}:{stat.st_mtime_ns}"


def is_settled(path):
    stat = os.stat(path)
    return time.time() - stat.st_mtime >= SETTLED_SECONDS


def iter_videos():
    pattern = os.path.join(VIDEO_DIR, VIDEO_GLOB)
    for path in sorted(glob.glob(pattern)):
        if os.path.isfile(path) and path.endswith("_timelapse.mp4"):
            yield path


def send_video(path, bot_token, chat_id):
    filename = os.path.basename(path)
    url = f"{API_BASE}/bot{bot_token}/sendVideo"
    data = {
        "chat_id": chat_id,
        "caption": filename,
        "supports_streaming": "true",
    }

    with open(path, "rb") as video:
        response = requests.post(
            url,
            data=data,
            files={"video": (filename, video, "video/mp4")},
            timeout=REQUEST_TIMEOUT,
        )

    if not response.ok:
        raise RuntimeError(f"Telegram API error {response.status_code}: {response.text}")


def process_once(state, bot_token, chat_id):
    changed = False
    for path in iter_videos():
        try:
            signature = file_signature(path)
            if state.get(path) == signature:
                continue
            if not is_settled(path):
                continue

            print(f"Sending {path} to Telegram...", flush=True)
            send_video(path, bot_token, chat_id)
            state[path] = signature
            save_state(state)
            changed = True
            print(f"Sent {path}", flush=True)
        except FileNotFoundError:
            continue
        except Exception as e:
            print(f"Failed to send {path}: {e}", flush=True)

    return changed


if __name__ == "__main__":
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not bot_token:
        raise SystemExit("TELEGRAM_BOT_TOKEN is required")
    if not chat_id:
        raise SystemExit("TELEGRAM_CHAT_ID is required")

    os.makedirs(VIDEO_DIR, exist_ok=True)
    state = load_state()
    print(f"Watching {VIDEO_DIR}/{VIDEO_GLOB} for Telegram delivery", flush=True)

    while True:
        process_once(state, bot_token, chat_id)
        time.sleep(POLL_INTERVAL)
