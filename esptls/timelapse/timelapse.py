import os
import time
import subprocess
import urllib.request
import urllib.parse
import json
from datetime import datetime, timedelta

PROCESSED_DIR = '/data/processed'
VIDEO_DIR = '/data/videos'

def send_telegram_message(text):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        return
    api_base = os.getenv("TELEGRAM_API_BASE", "https://api.telegram.org")
    url = f"{api_base}/bot{bot_token}/sendMessage"
    
    data = json.dumps({"chat_id": chat_id, "text": f"⚠️ [Timelapse] {text}"}).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=data,
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            response.read()
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

def is_valid_jpeg(file_path):
    # 1. Fast check: JPEG SOI and EOI markers
    try:
        size = os.path.getsize(file_path)
        if size < 4:
            return False
        with open(file_path, 'rb') as f:
            if f.read(2) != b'\xff\xd8':
                return False
            f.seek(-min(size, 64), os.SEEK_END)
            tail = f.read()
            if b'\xff\xd9' in tail:
                return True
    except Exception:
        return False
        
    # 2. Slow fallback check using ffmpeg (only if fast check failed)
    cmd = ['ffmpeg', '-v', 'error', '-i', file_path, '-f', 'null', '-']
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode == 0:
            return True
        print(f"File {file_path} is corrupt (ffmpeg returned {res.returncode}): {res.stderr.strip()}")
    except Exception as e:
        # If ffmpeg is not available, default to True to avoid deleting valid files
        print(f"ffmpeg check failed for {file_path}: {e}")
        return True
    return False

def create_timelapse():
    today = datetime.now().strftime('%Y%m%d')
    
    # Find all unique dates in processed directory
    dates = set()
    if os.path.exists(PROCESSED_DIR):
        for f in os.listdir(PROCESSED_DIR):
            if f.endswith('_processed.jpg') and len(f) >= 8:
                dates.add(f[:8])
                
    for date_str in sorted(dates):
        if date_str >= today:
            continue
            
        print(f"Starting timelapse for {date_str}...")
        files = sorted([f for f in os.listdir(PROCESSED_DIR) if f.startswith(date_str) and f.endswith('_processed.jpg')])
        
        # Filter and remove corrupt files
        valid_files = []
        for filename in files:
            file_path = os.path.join(PROCESSED_DIR, filename)
            if is_valid_jpeg(file_path):
                valid_files.append(filename)
            else:
                print(f"Deleting corrupt processed file: {file_path}")
                send_telegram_message(f"Deleted corrupt processed image: {filename}")
                try:
                    os.remove(file_path)
                except Exception as rm_err:
                    print(f"Error removing corrupt file {file_path}: {rm_err}")
                    
        files = valid_files
        if not files:
            print(f"No valid files left for date {date_str}.")
            continue

        # Create a concat file for ffmpeg
        concat_file = f"/tmp/{date_str}_list.txt"
        with open(concat_file, 'w') as f:
            for filename in files:
                f.write(f"file '{os.path.join(PROCESSED_DIR, filename)}'\n")
                f.write(f"duration 0.03333\n") # 10 fps

        output_video = os.path.join(VIDEO_DIR, f"{date_str}_timelapse.mp4")
        
        # FFmpeg command
        cmd = [
            'ffmpeg', '-y',
            '-f', 'concat', '-safe', '0',
            '-i', concat_file,
            '-movflags', '+faststart',
            '-c:v', 'libx264',
            '-crf', '30',
            '-preset', 'medium',
            '-vf', 'format=yuv420p',
            output_video
        ]
        
        try:
            subprocess.run(cmd, check=True)
            print(f"Timelapse created: {output_video}")
            for filename in files:
                try:
                    os.remove(os.path.join(PROCESSED_DIR, filename))
                except FileNotFoundError:
                    pass
        except Exception as e:
            print(f"FFmpeg error: {e}")
        finally:
            if os.path.exists(concat_file):
                os.remove(concat_file)

if __name__ == "__main__":
    os.makedirs(VIDEO_DIR, exist_ok=True)
    
    run_immediately = os.getenv('RUN_IMMEDIATELY', 'false').lower() in ('true', '1', 't')
    run_hour = int(os.getenv('RUN_HOUR', '11'))
    
    if run_immediately:
        print("RUN_IMMEDIATELY is set, starting now...")
        create_timelapse()

    print(f"Scheduler started. Will run daily at {run_hour}:00")
    while True:
        now = datetime.now()
        if now.hour == run_hour:
            create_timelapse()
            # Wait until next hour to avoid re-triggering in the same hour
            print(f"Task finished at {now.strftime('%H:%M:%S')}. Sleeping until next hour...")
            time.sleep(3600)
        else:
            time.sleep(600) # Check every 10 minutes
