import os
import time
import subprocess
import requests
from datetime import datetime, timedelta
from influxdb_client import InfluxDBClient
from PIL import Image, ImageDraw, ImageFont

# Configuration
RAW_DIR = '/data/raw'
PROCESSED_DIR = '/data/processed'
INFLUX_URL = os.getenv('INFLUX_URL')
INFLUX_TOKEN = os.getenv('INFLUX_TOKEN')
INFLUX_ORG = os.getenv('INFLUX_ORG')
INFLUX_BUCKET = os.getenv('INFLUX_BUCKET')

print(f"Processor starting. Raw: {RAW_DIR}, Processed: {PROCESSED_DIR}")

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
query_api = client.query_api()

def get_metadata_from_filename(filename):
    parts = filename.split('_')
    dt_str = parts[0] + parts[1]
    dt = datetime.strptime(dt_str, '%Y%m%d%H%M%S')
    # dt is naive local time (matching ESP/Container TZ)
    mode = parts[2].split('.')[0]
    return dt, mode

def get_influx_data(image_time):
    # Convert local image_time to UTC for InfluxDB query
    # astimezone() without args uses system local timezone
    local_tz = datetime.now().astimezone().tzinfo
    image_time_utc = image_time.replace(tzinfo=local_tz).astimezone(timedelta(0))
    
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
    
    # 1. Fuse if multiple
    if len(files) > 1:
        input_paths = [os.path.join(RAW_DIR, f) for f in files]
        fused_tmp = "/tmp/fused.jpg"
        # Fix: Use input_paths instead of files list in subprocess
        print(f"Executing: enfuse --output={fused_tmp} {' '.join(input_paths)}")
        subprocess.run(['enfuse', '--output=' + fused_tmp] + input_paths, check=True)
        img = Image.open(fused_tmp)
    else:
        img = Image.open(os.path.join(RAW_DIR, files[0]))
    
    # 2. Overlay Metadata
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
        text_lines.append(dt.strftime('%Y-%m-%d %H:%M:%S'))
    
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
    
    # 3. Cleanup raw
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
        dt, mode = get_metadata_from_filename(first_file)
        
        target = 1
        if mode == 'night': target = 3
        elif mode in ['sunset', 'sunrise']: target = 2
        
        current_set = [first_file]
        last_dt = dt
        
        # Look for matching files in the same mode and close in time
        for next_file in all_files[1:]:
            if len(current_set) >= target: break
            ndt, nmode = get_metadata_from_filename(next_file)
            
            # Group if same mode and within 65 seconds of last image
            if nmode == mode and (ndt - last_dt).total_seconds() <= 65:
                current_set.append(next_file)
                last_dt = ndt
            else:
                break
        
        if len(current_set) == target:
            process_set(current_set)
        else:
            # Check age using local time (since filename is local)
            age = (datetime.now() - dt).total_seconds()
            if age > 600:
                print(f"Processing incomplete set (orphan, age {int(age)}s): {current_set}")
                process_set(current_set)
            else:
                if len(all_files) > 1: # Only log if there are other files but they didn't match
                    print(f"Waiting for set: {mode} {len(current_set)}/{target} (First: {first_file}, Age: {int(age)}s)")
                time.sleep(5)
        
        time.sleep(1)


if __name__ == "__main__":
    run_processor()
