import requests
import re
import os
from bs4 import BeautifulSoup
from influxdb_client import InfluxDBClient

# Scraping the website
url = "https://fam-lange.de/wetter.php"
response = requests.get(url)
soup = BeautifulSoup(response.content, "html.parser")

# Find the card with the header 'Windrichtung'
winddirection_card = soup.find("div", class_="card-header", string="Windrichtung")

if winddirection_card:
    # The value is in the next sibling card-body
    winddirection_value = winddirection_card.find_next("div", class_="card-body").find("h5", class_="card-title").text.strip()
    # Extract numeric value (winddirection)
    winddirection_value = re.sub(r'[^\d.-]', '', winddirection_value)  # Remove non-digit, non-dot, non-minus characters
    print(f"Wind direction: {winddirection_value}°")
else:
    print("Wind direction value not found on the website.")
    exit()

# Writing to InfluxDB
#winddirection_value = 15
bucket = "wetter"
org = "org"
token = os.environ.get("INFLUXDB_TOKEN")
url = "https://influxdb.ioui.eu"
client = InfluxDBClient(url=url, token=token, org=org, verify_ssl=False)
write_api = client.write_api()

data = f"winddirection value={winddirection_value}"
write_api.write(bucket=bucket, org=org, record=data)

print(f"WindDirection value {winddirection_value} written to InfluxDB.")

write_api.close()
client.close()

