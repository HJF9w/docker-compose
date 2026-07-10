#!/usr/bin/env python3
import os
import sys
import shlex
import logging
import subprocess
import tempfile
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import requests

def get_config():
    """Load configuration from environment variables."""
    config = {
        "bot_token": os.environ.get("TELEGRAM_BOT_TOKEN"),
        "chat_id": os.environ.get("TELEGRAM_CHAT_ID"),
        "neon_host": os.environ.get("NEON_HOST", "neon.example.org"),
        "http_user": os.environ.get("HTTP_USER"),
        "http_pass": os.environ.get("HTTP_PASS"),
        "download_method": os.environ.get("DOWNLOAD_METHOD", "scp").lower(),
        "ssh_user": os.environ.get("SSH_USER", "user"),
        "ssh_host": os.environ.get("SSH_HOST"),
        "ssh_port": int(os.environ.get("SSH_PORT", "22")),
        "ssh_key": os.environ.get("SSH_KEY"),
        "ssh_key_file": os.environ.get("SSH_KEY_FILE"),
        "delay_days": int(os.environ.get("DELAY_DAYS", "2")),
        "tz_name": os.environ.get("TZ", "Europe/Berlin"),
        "video_height": int(os.environ.get("VIDEO_HEIGHT", "1944")),
        "video_width": int(os.environ.get("VIDEO_WIDTH", "2592")),
        "ffmpeg_args": os.environ.get(
            "FFMPEG_ARGS",
            "-movflags +faststart -c:v libx264 -b:v 2M -maxrate 2M -bufsize 4M"
        ),
        "startrails_url_template": os.environ.get(
            "STARTRAILS_URL_TEMPLATE",
            "http://{host}/images/{date_str}/startrails/startrails-{date_str}.jpg"
        ),
        "keogram_url_template": os.environ.get(
            "KEOGRAM_URL_TEMPLATE",
            "http://{host}/images/{date_str}/keogram/keogram-{date_str}.jpg"
        ),
        "video_url_template": os.environ.get(
            "VIDEO_URL_TEMPLATE",
            "http://{host}/images/{date_str}/allsky-{date_str}.mp4"
        ),
        "ssh_path_template": os.environ.get(
            "SSH_PATH_TEMPLATE",
            "/home/{user}/allsky/images/{date_str}/allsky-{date_str}.mp4"
        )
    }
    
    # Fallback SSH host to Neon host if not specified
    if not config["ssh_host"]:
        config["ssh_host"] = config["neon_host"]
        
    return config

def setup_logging():
    """Setup logging to stdout and optionally to /logs/tl_conv.log."""
    log_level = logging.DEBUG if os.environ.get("DEBUG", "").lower() in ("true", "1", "yes") else logging.INFO
    log_dir = os.environ.get("LOG_DIR", "/logs")
    log_handlers = [logging.StreamHandler(sys.stdout)]
    
    if os.path.exists(log_dir) and os.access(log_dir, os.W_OK):
        log_handlers.append(logging.FileHandler(os.path.join(log_dir, "tl_conv.log")))
        
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=log_handlers
    )
    logging.info("Logging initialized.")

def call_telegram_api(token, method, data=None, files=None):
    """Wrapper to make standard POST requests to the Telegram Bot API."""
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set")
    url = f"https://api.telegram.org/bot{token}/{method}"
    logging.debug(f"Calling Telegram API endpoint: {method}")
    
    try:
        response = requests.post(url, data=data, files=files, timeout=90)
        response.raise_for_status()
        res_json = response.json()
        if not res_json.get("ok"):
            logging.error(f"Telegram API returned ok=False for {method}: {res_json}")
            raise RuntimeError(f"Telegram API error: {res_json}")
        return res_json
    except Exception as e:
        logging.error(f"HTTP request to Telegram API {method} failed: {e}")
        raise

def delete_message(token, chat_id, message_id):
    """Delete a Telegram message. Fails gracefully so workflow is not aborted."""
    try:
        call_telegram_api(token, "deleteMessage", data={"chat_id": chat_id, "message_id": message_id})
        logging.info(f"Successfully deleted message ID: {message_id}")
    except Exception as e:
        logging.warning(f"Failed to delete message ID {message_id} (non-fatal): {e}")

def download_http(url, local_path, user=None, password=None):
    """Download a file over HTTP(S) with optional basic authentication."""
    logging.info(f"Downloading from HTTP URL: {url}")
    auth = (user, password) if user and password else None
    try:
        with requests.get(url, auth=auth, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(local_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        logging.info(f"Successfully downloaded to {local_path}")
    except Exception as e:
        logging.error(f"HTTP download failed from {url}: {e}")
        raise

def download_scp(remote_path, local_path, user, host, port=22, key_path=None):
    """Download a file using SCP with host key checks disabled."""
    logging.info(f"Downloading via SCP from {user}@{host}:{remote_path} to {local_path}")
    
    cmd = [
        "scp",
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-P", str(port)
    ]
    if key_path:
        cmd += ["-i", key_path]
        
    cmd += [f"{user}@{host}:{remote_path}", local_path]
    
    logging.debug(f"Running SCP command: {' '.join(cmd)}")
    try:
        res = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logging.info("SCP download completed successfully.")
        logging.debug(f"SCP stdout: {res.stdout}")
    except subprocess.CalledProcessError as e:
        logging.error(f"SCP download failed. Stderr: {e.stderr}")
        raise

def convert_video(input_path, output_path, ffmpeg_args_str):
    """Convert video with ffmpeg using the provided argument string."""
    logging.info(f"Converting video {input_path} to {output_path}")
    args = shlex.split(ffmpeg_args_str)
    
    cmd = ["ffmpeg", "-y", "-i", input_path] + args + [output_path]
    logging.info(f"Running FFMPEG: {' '.join(cmd)}")
    try:
        res = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logging.info("FFMPEG conversion completed successfully.")
        logging.debug(f"FFMPEG stdout: {res.stdout}")
    except subprocess.CalledProcessError as e:
        logging.error(f"FFMPEG conversion failed. Stderr: {e.stderr}")
        raise

def main():
    setup_logging()
    config = get_config()
    
    # Check essential variables
    if not config["bot_token"] or not config["chat_id"]:
        logging.error("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set.")
        sys.exit(1)
        
    # Get datetime in configured timezone
    try:
        tz = ZoneInfo(config["tz_name"])
    except Exception as e:
        logging.warning(f"Invalid timezone {config['tz_name']}, falling back to UTC. Error: {e}")
        tz = ZoneInfo("UTC")
        
    now = datetime.now(tz)
    target_date = now - timedelta(days=config["delay_days"])
    date_str = target_date.strftime("%Y%m%d")
    
    logging.info(f"Current local time in timezone {config['tz_name']}: {now}")
    logging.info(f"Target date (delay days = {config['delay_days']}): {date_str}")
    
    # 1. Send "Started Workflow" notification
    status_text = f"Started Allsky Telegram Workflow at {now.strftime('%Y-%m-%d %H:%M:%S %Z')}"
    logging.info(f"Sending work notification to Telegram: '{status_text}'")
    notify_res = call_telegram_api(config["bot_token"], "sendMessage", data={
        "chat_id": config["chat_id"],
        "text": status_text,
        "disable_notification": "true"
    })
    work_notification_msg_id = notify_res["result"]["message_id"]
    
    # Setup temporary directory for downloads/processing
    temp_dir = tempfile.TemporaryDirectory()
    logging.info(f"Created temporary directory: {temp_dir.name}")
    
    ssh_key_file = None
    try:
        # Determine path to the source video file
        local_input_video = os.path.join(temp_dir.name, "input.mp4")
        local_output_video = os.path.join(temp_dir.name, "output.mp4")
        
        # 2. Download Timelapse Video
        if config["download_method"] == "http":
            video_url = config["video_url_template"].format(host=config["neon_host"], date_str=date_str)
            download_http(video_url, local_input_video, config["http_user"], config["http_pass"])
        else:
            # Default to SCP
            remote_path = config["ssh_path_template"].format(user=config["ssh_user"], date_str=date_str)
            
            # Handle SSH Key from environment variable
            if config["ssh_key"]:
                fd, ssh_key_file = tempfile.mkstemp()
                os.close(fd)
                with open(ssh_key_file, "w") as f:
                    f.write(config["ssh_key"].strip() + "\n")
                os.chmod(ssh_key_file, 0o600)
                key_path = ssh_key_file
            elif config["ssh_key_file"]:
                key_path = config["ssh_key_file"]
            else:
                key_path = None
                
            download_scp(
                remote_path=remote_path,
                local_path=local_input_video,
                user=config["ssh_user"],
                host=config["ssh_host"],
                port=config["ssh_port"],
                key_path=key_path
            )
            
        # 3. Convert Video with ffmpeg
        convert_video(local_input_video, local_output_video, config["ffmpeg_args"])
        
        # 4. Upload converted video to Telegram (to get file_id)
        logging.info("Uploading converted video to Telegram to obtain file_id...")
        with open(local_output_video, "rb") as video_file:
            video_res = call_telegram_api(config["bot_token"], "sendVideo", data={
                "chat_id": config["chat_id"],
                "disable_notification": "true",
                "width": config["video_width"],
                "height": config["video_height"],
                "supports_streaming": "true"
            }, files={"video": video_file})
            
        res_data = video_res.get("result", {})
        if "video" in res_data:
            video_file_id = res_data["video"]["file_id"]
        elif "document" in res_data:
            video_file_id = res_data["document"]["file_id"]
        else:
            raise KeyError("Failed to extract video file_id from Telegram response")
            
        video_msg_id = res_data["message_id"]
        logging.info(f"Video uploaded. file_id: {video_file_id}, message_id: {video_msg_id}")
        
        # Immediately delete the upload message
        delete_message(config["bot_token"], config["chat_id"], video_msg_id)
        
        # 5. Download and Upload Startrails photo
        local_startrails = os.path.join(temp_dir.name, "startrails.jpg")
        startrails_url = config["startrails_url_template"].format(host=config["neon_host"], date_str=date_str)
        download_http(startrails_url, local_startrails, config["http_user"], config["http_pass"])
        
        logging.info("Uploading Startrails photo to Telegram to obtain file_id...")
        with open(local_startrails, "rb") as photo_file:
            startrails_res = call_telegram_api(config["bot_token"], "sendPhoto", data={
                "chat_id": config["chat_id"],
                "disable_notification": "true"
            }, files={"photo": photo_file})
            
        startrails_file_id = startrails_res["result"]["photo"][-1]["file_id"]
        startrails_msg_id = startrails_res["result"]["message_id"]
        logging.info(f"Startrails uploaded. file_id: {startrails_file_id}, message_id: {startrails_msg_id}")
        
        delete_message(config["bot_token"], config["chat_id"], startrails_msg_id)
        
        # 6. Download and Upload Keogram photo
        local_keogram = os.path.join(temp_dir.name, "keogram.jpg")
        keogram_url = config["keogram_url_template"].format(host=config["neon_host"], date_str=date_str)
        download_http(keogram_url, local_keogram, config["http_user"], config["http_pass"])
        
        logging.info("Uploading Keogram photo to Telegram to obtain file_id...")
        with open(local_keogram, "rb") as photo_file:
            keogram_res = call_telegram_api(config["bot_token"], "sendPhoto", data={
                "chat_id": config["chat_id"],
                "disable_notification": "true"
            }, files={"photo": photo_file})
            
        keogram_file_id = keogram_res["result"]["photo"][-1]["file_id"]
        keogram_msg_id = keogram_res["result"]["message_id"]
        logging.info(f"Keogram uploaded. file_id: {keogram_file_id}, message_id: {keogram_msg_id}")
        
        delete_message(config["bot_token"], config["chat_id"], keogram_msg_id)
        
        # 7. Send the Media Group (Album)
        logging.info("Sending final Media Group (Album)...")
        media_group = [
            {
                "type": "photo",
                "media": keogram_file_id
            },
            {
                "type": "photo",
                "media": startrails_file_id
            },
            {
                "type": "video",
                "media": video_file_id
            }
        ]
        call_telegram_api(config["bot_token"], "sendMediaGroup", data={
            "chat_id": config["chat_id"],
            "media": json.dumps(media_group)
        })
        logging.info("Media Group sent successfully.")
        
        # 8. Delete the "Started Workflow" notification
        delete_message(config["bot_token"], config["chat_id"], work_notification_msg_id)
        
        logging.info("Allsky Telegram Workflow completed successfully.")
        
    except Exception as e:
        logging.exception(f"Workflow execution failed with error: {e}")
        # Make sure to clean up the started message if we failed
        delete_message(config["bot_token"], config["chat_id"], work_notification_msg_id)
        sys.exit(1)
        
    finally:
        # Cleanup temp key file
        if ssh_key_file and os.path.exists(ssh_key_file):
            try:
                os.remove(ssh_key_file)
                logging.debug("Temporary SSH key file removed.")
            except Exception as e:
                logging.warning(f"Failed to remove temp SSH key: {e}")
                
        # Cleanup temp directory
        try:
            temp_dir.cleanup()
            logging.info("Temporary files cleaned up.")
        except Exception as e:
            logging.warning(f"Failed to clean up temporary directory: {e}")

if __name__ == "__main__":
    main()
