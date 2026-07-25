import os
import time
import requests
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from influxdb_client import InfluxDBClient
from PIL import Image, ImageDraw, ImageFont, ImageFile

# Configuration
RAW_DIR = '/data/raw'
PROCESSED_DIR = '/data/processed'
INFLUX_URL = os.getenv('INFLUX_URL')
INFLUX_TOKEN = os.getenv('INFLUX_TOKEN')
INFLUX_ORG = os.getenv('INFLUX_ORG')
INFLUX_BUCKET = os.getenv('INFLUX_BUCKET')
LOCAL_TZ = ZoneInfo(os.getenv('TZ', 'Europe/Brussels'))

print(f"Processor starting. Raw: {RAW_DIR}, Processed: {PROCESSED_DIR}")

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
query_api = client.query_api()

def send_telegram_message(text):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        return
    api_base = os.getenv("TELEGRAM_API_BASE", "https://api.telegram.org")
    url = f"{api_base}/bot{bot_token}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": f"⚠️ [Processor] {text}"}, timeout=10)
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

def get_metadata_from_filename(filename):
    parts = filename.split('_')
    dt_str = parts[0] + parts[1]
    # Filenames are UTC timestamps from the ESP
    dt = datetime.strptime(dt_str, '%Y%m%d%H%M%S').replace(tzinfo=timezone.utc)
    mode = parts[2].split('.')[0]
    return dt, mode

def get_influx_data(image_time):
    # image_time is aware local time
    image_time_utc = image_time.astimezone(timezone.utc)
    
    start = image_time_utc - timedelta(minutes=10)
    stop = image_time_utc + timedelta(minutes=10)
    
    query = f'''
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: {start.strftime('%Y-%m-%dT%H:%M:%SZ')}, stop: {stop.strftime('%Y-%m-%dT%H:%M:%SZ')})
      |> filter(fn: (r) => r["_measurement"] == "esp32cam_status")
      |> last()
    '''
    try:
        result = query_api.query(org=INFLUX_ORG, query=query)
        data = {}
        for table in result:
            for record in table.records:
                data[record.get_field()] = record.get_value()
        return data
    except Exception as e:
        print(f"Influx query error: {e}")
        return {}

def process_set(files):
    if not files: return
    
    output_name = files[0].replace('.jpg', '_processed.jpg')
    output_path = os.path.join(PROCESSED_DIR, output_name)
    print(f"Processing set (size {len(files)}): {files}")
    
    try:
        # 1. Validate and attempt recovery of each file
        valid_files = []
        for f in files:
            f_path = os.path.join(RAW_DIR, f)
            
            if not os.path.exists(f_path):
                print(f"File not found: {f_path}")
                continue
            if os.path.getsize(f_path) == 0:
                print(f"File is empty: {f_path}. Deleting.")
                send_telegram_message(f"Deleted empty file: {f}")
                try:
                    os.remove(f_path)
                except Exception as rm_err:
                    print(f"Error removing empty file {f_path}: {rm_err}")
                continue
                
            # Try loading normally
            try:
                with Image.open(f_path) as img:
                    img.load()
                valid_files.append(f)
                continue
            except Exception as e:
                print(f"Image {f} failed to load normally: {e}. Attempting recovery...")
                
            # Try to recover using LOAD_TRUNCATED_IMAGES = True
            ImageFile.LOAD_TRUNCATED_IMAGES = True
            temp_path = f_path + ".tmp"
            try:
                with Image.open(f_path) as img:
                    img.load()
                    img.save(temp_path, "JPEG", quality=90)
                os.replace(temp_path, f_path)
                print(f"Successfully recovered/re-saved truncated image {f}.")
                send_telegram_message(f"Recovered/re-saved truncated image: {f}")
                valid_files.append(f)
            except Exception as recovery_error:
                print(f"Failed to recover image {f}: {recovery_error}. Deleting corrupt file.")
                send_telegram_message(f"Deleted corrupt file {f} (failed validation & recovery). Error: {recovery_error}")
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass
                try:
                    os.remove(f_path)
                except Exception as rm_err:
                    print(f"Error removing corrupt file {f_path}: {rm_err}")
            finally:
                ImageFile.LOAD_TRUNCATED_IMAGES = False
                
        files = valid_files
        if not files:
            print("No valid or recoverable files left in the set.")
            return

        # 2. Open first image
        img = None
        try:
            img = Image.open(os.path.join(RAW_DIR, files[0]))
        except Exception as e:
            print(f"Failed to open first image {files[0]}: {e}. Skipping set and cleaning up.")
            send_telegram_message(f"Failed to open/process first image {files[0]}. Skipping and deleting set: {files}. Error: {e}")
            for f in files:
                try:
                    os.remove(os.path.join(RAW_DIR, f))
                except Exception:
                    pass
            return

        # 3. Overlay Metadata
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
        except:
            font = ImageFont.load_default()
            
        main_time, _ = get_metadata_from_filename(files[0])
        influx_data = get_influx_data(main_time)
        
        text_lines = []
        # Sort files by time for the overlay
        sorted_files = sorted(files)
        for f in sorted_files:
            dt, _ = get_metadata_from_filename(f)
            # Convert UTC to local time for display
            local_dt = dt.astimezone(LOCAL_TZ)
            text_lines.append(local_dt.strftime('%Y-%m-%d %H:%M:%S'))
        
        if influx_data:
            text_lines.append(f"CPU: {influx_data.get('temp_cpu', 'N/A')}°C")
            text_lines.append(f"Ext: {influx_data.get('temp_ext', 'N/A')}°C")
            text_lines.append(f"RSSI: {influx_data.get('wifi_rssi', 'N/A')}dBm")
        
        y_offset = img.height - (len(text_lines) * 25) - 10
        for line in text_lines:
            draw.text((img.width - 250 + 2, y_offset + 2), line, font=font, fill="black")
            draw.text((img.width - 250, y_offset), line, font=font, fill="white")
            y_offset += 25
            
        img.save(output_path, "JPEG", quality=90)
        print(f"Success: {output_name}")
        
    except Exception as e:
        print(f"Unexpected error processing set: {e}")
        
    finally:
        # 4. Cleanup raw
        for f in files:
            try:
                os.remove(os.path.join(RAW_DIR, f))
            except FileNotFoundError:
                pass

def cleanup_processed():
    now = time.time()
    for f in os.listdir(PROCESSED_DIR):
        if not f.endswith('.jpg'): continue
        f_path = os.path.join(PROCESSED_DIR, f)
        if os.path.getmtime(f_path) < now - (4 * 24 * 3600):
            os.remove(f_path)
            print(f"Cleaned up old image: {f}")

def run_processor():
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    while True:
        all_files = sorted([f for f in os.listdir(RAW_DIR) if f.endswith('.jpg')])
        if not all_files:
            time.sleep(10)
            cleanup_processed()
            continue

        first_file = all_files[0]
        try:
            get_metadata_from_filename(first_file)
        except Exception as e:
            print(f"Invalid filename format: {first_file}. Error: {e}. Deleting file.")
            send_telegram_message(f"Deleted file {first_file} due to invalid filename format. Error: {e}")
            try:
                os.remove(os.path.join(RAW_DIR, first_file))
            except Exception:
                pass
            continue

        process_set([first_file])
        time.sleep(1)

if __name__ == "__main__":
    run_processor()
