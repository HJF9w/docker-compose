import os
import time
import requests

ESP_IP = os.getenv('ESP_IP')
RAW_DIR = '/data/raw'
SYNCED_FILE = '/data/synced.txt'

print(f"Downloader starting. ESP_IP: {ESP_IP}")

def get_synced_files():
    if not os.path.exists(SYNCED_FILE):
        return set()
    with open(SYNCED_FILE, 'r') as f:
        return set(line.strip() for line in f)

def add_synced_file(filename):
    with open(SYNCED_FILE, 'a') as f:
        f.write(filename + '\n')

def download_files():
    print(f"--- Checking for new files at {datetime.now().strftime('%H:%M:%S')} ---")
    try:
        r = requests.get(f'http://{ESP_IP}/file_list', timeout=10)
        r.raise_for_status()
        files = r.json()
        print(f"Found {len(files)} files on ESP")
    except Exception as e:
        print(f"Error fetching file list from {ESP_IP}: {e}")
        return

    synced = get_synced_files()
    new_count = 0

    for f_info in files:
        name = f_info['name']
        size = f_info['size']
        
        if name in synced:
            continue
            
        new_count += 1
        print(f"Downloading {name} ({size} bytes)...")
        try:
            # Download
            dr = requests.get(f'http://{ESP_IP}/file?path=/{name}', timeout=30)
            dr.raise_for_status()
            
            if len(dr.content) != size:
                print(f"Size mismatch for {name}: expected {size}, got {len(dr.content)}")
                continue
                
            local_path = os.path.join(RAW_DIR, name)
            with open(local_path, 'wb') as f:
                f.write(dr.content)
            
            # Verify local file exists and is correct size
            if os.path.getsize(local_path) == size:
                # Delete from ESP
                del_r = requests.get(f'http://{ESP_IP}/file_delete?path=/{name}', timeout=10)
                if del_r.status_code == 200:
                    add_synced_file(name)
                    print(f"Successfully synced and deleted {name}")
                else:
                    print(f"Warning: Downloaded {name} but failed to delete from ESP (Status: {del_r.status_code})")
            
        except Exception as e:
            print(f"Error downloading {name}: {e}")
            
    if new_count == 0:
        print("No new files to download")

if __name__ == "__main__":
    from datetime import datetime
    os.makedirs(RAW_DIR, exist_ok=True)
    while True:
        download_files()
        time.sleep(60)
