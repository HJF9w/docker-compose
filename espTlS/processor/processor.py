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

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
query_api = client.query_api()

def get_metadata_from_filename(filename):
    # Example: 20260321_120000_daytime.jpg
    parts = filename.split('_')
    dt_str = parts[0] + parts[1]
    dt = datetime.strptime(dt_str, '%Y%m%d%H%M%S')
    mode = parts[2].split('.')[0]
    return dt, mode

def get_influx_data(image_time):
    # Query for the closest data within 10 minutes
    start = image_time - timedelta(minutes=10)
    stop = image_time + timedelta(minutes=10)
    
    query = f'''
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: {start.isoformat()}Z, stop: {stop.isoformat()}Z)
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
    # files is a list of filenames
    if not files: return
    
    output_name = files[0].replace('.jpg', '_processed.jpg')
    output_path = os.path.join(PROCESSED_DIR, output_name)
    
    # 1. Fuse if multiple
    if len(files) > 1:
        input_paths = [os.path.join(RAW_DIR, f) for f in files]
        fused_tmp = "/tmp/fused.jpg"
        subprocess.run(['enfuse', '--output=' + fused_tmp] + input_paths, check=True)
        img = Image.open(fused_tmp)
    else:
        img = Image.open(os.path.join(RAW_DIR, files[0]))
    
    # 2. Overlay Metadata
    draw = ImageDraw.Draw(img)
    # Use a basic font
    try:
        font = ImageFont.truetype("/usr/share/fonts/ttf-dejavu/DejaVuSans.ttf", 20)
    except:
        font = ImageFont.load_default()
        
    main_time, _ = get_metadata_from_filename(files[0])
    influx_data = get_influx_data(main_time)
    
    text_lines = []
    # Add timestamps for all combined files
    for f in files:
        dt, _ = get_metadata_from_filename(f)
        text_lines.append(dt.strftime('%Y-%m-%d %H:%M:%S'))
    
    # Add status info
    if influx_data:
        text_lines.append(f"CPU: {influx_data.get('temp_cpu', 'N/A')}°C")
        text_lines.append(f"Ext: {influx_data.get('temp_ext', 'N/A')}°C")
        text_lines.append(f"RSSI: {influx_data.get('wifi_rssi', 'N/A')}dBm")
    
    y_offset = img.height - (len(text_lines) * 25) - 10
    for line in text_lines:
        # Draw shadow for readability
        draw.text((img.width - 250 + 2, y_offset + 2), line, font=font, fill="black")
        draw.text((img.width - 250, y_offset), line, font=font, fill="white")
        y_offset += 25
        
    img.save(output_path, "JPEG", quality=90)
    print(f"Processed: {output_name}")
    
    # 3. Cleanup raw
    for f in files:
        os.remove(os.path.join(RAW_DIR, f))

def cleanup_processed():
    now = time.time()
    for f in os.listdir(PROCESSED_DIR):
        f_path = os.path.join(PROCESSED_DIR, f)
        if os.path.getmtime(f_path) < now - (4 * 24 * 3600):
            os.remove(f_path)
            print(f"Cleaned up old image: {f}")

def run_processor():
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    while True:
        all_files = sorted([f for f in os.listdir(RAW_DIR) if f.endswith('.jpg')])
        if not all_files:
            time.sleep(30)
            cleanup_processed()
            continue
            
        # Grouping logic
        current_set = []
        first_file = all_files[0]
        dt, mode = get_metadata_from_filename(first_file)
        
        target = 1
        if mode == 'night': target = 3
        elif mode == 'sunset' or mode == 'sunrise': target = 2
        
        # Look for consecutive files within 60s
        current_set.append(first_file)
        last_dt = dt
        
        for next_file in all_files[1:]:
            if len(current_set) >= target: break
            ndt, nmode = get_metadata_from_filename(next_file)
            if (ndt - last_dt).total_seconds() < 60:
                current_set.append(next_file)
                last_dt = ndt
            else:
                break
        
        if len(current_set) == target:
            process_set(current_set)
        else:
            # Orphan check
            if (datetime.now() - dt).total_seconds() > 600:
                print(f"Deleting orphan: {first_file}")
                os.remove(os.path.join(RAW_DIR, first_file))
            else:
                # Wait for more images
                time.sleep(10)
        
        time.sleep(1)

if __name__ == "__main__":
    run_processor()
