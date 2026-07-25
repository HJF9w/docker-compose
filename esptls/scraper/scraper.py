import os
import time
import requests
from requests.auth import HTTPDigestAuth
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import datetime

ESP_IP = os.getenv('ESP_IP')
URL = os.getenv('INFLUX_URL')
TOKEN = os.getenv('INFLUX_TOKEN')
ORG = os.getenv('INFLUX_ORG')
BUCKET = os.getenv('INFLUX_BUCKET')
ESP_USER = os.getenv('ESP_USER')
ESP_PASS = os.getenv('ESP_PASS')

auth = HTTPDigestAuth(ESP_USER, ESP_PASS) if ESP_USER and ESP_PASS else None

print(f"Scraper starting. ESP_IP: {ESP_IP}, Influx: {URL}")

client = InfluxDBClient(url=URL, token=TOKEN, org=ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)

def scrape():
    ts = datetime.now().strftime('%H:%M:%S')
    try:
        r = requests.get(f'http://{ESP_IP}/status', timeout=10, auth=auth)
        r.raise_for_status()
        data = r.json()
        print(f"[{ts}] Status fetched from ESP. RSSI: {data.get('wifi_rssi', 'N/A')}")
        
        point = Point("esp32cam_status").tag("host", "esp32-cam-1")
        
        # Tags: Categorical data
        for tag_key in ["mode", "wifi_ssid", "wifi_ip", "sd_mounted", "running"]:
            if tag_key in data:
                point.tag(tag_key, str(data[tag_key]))
        
        # Fields: All data points
        for key, value in data.items():
            if isinstance(value, (int, float, bool)):
                point.field(key, value)
            else:
                # String fields (last_file, time_str, etc)
                point.field(key, str(value))
        
        write_api.write(bucket=BUCKET, org=ORG, record=point)
        print(f"[{ts}] All {len(data)} metrics written to InfluxDB")
    except Exception as e:
        print(f"[{ts}] Scraper error: {e}")

if __name__ == "__main__":
    while True:
        scrape()
        time.sleep(300)
