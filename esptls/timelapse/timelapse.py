import os
import time
import subprocess
from datetime import datetime, timedelta

PROCESSED_DIR = '/data/processed'
VIDEO_DIR = '/data/videos'

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
        
        if not files:
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
            '-c:v', 'libx264',
            '-crf', '26',
            '-preset', 'slow',
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
