import os
import time
import requests
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

ESP_IP = os.getenv('ESP_IP')
URL = os.getenv('INFLUX_URL')
TOKEN = os.getenv('INFLUX_TOKEN')
ORG = os.getenv('INFLUX_ORG')
BUCKET = os.getenv('INFLUX_BUCKET')

client = InfluxDBClient(url=URL, token=TOKEN, org=ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)

def scrape():
    try:
        r = requests.get(f'http://{ESP_IP}/status', timeout=10)
        r.raise_for_status()
        data = r.json()
        
        point = Point("esp32cam_status") \
            .tag("host", "esp32-cam-1") \
            .field("temp_cpu", float(data['temp_cpu'])) \
            .field("temp_ext", float(data['temp_ext'])) \
            .field("wifi_rssi", int(data['wifi_rssi'])) \
            .field("storage_percent", float(data['storage_percent'])) \
            .field("aec", int(data['aec'])) \
            .field("agc", int(data['agc'])) \
            .field("sun_elevation", float(data['sun_elevation']))
        
        write_api.write(bucket=BUCKET, org=ORG, record=point)
        print("Metrics written to InfluxDB")
    except Exception as e:
        print(f"Scraper error: {e}")

if __name__ == "__main__":
    while True:
        scrape()
        time.sleep(300)
