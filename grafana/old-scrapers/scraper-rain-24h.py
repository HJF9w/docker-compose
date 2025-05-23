import requests
import re
import os
from bs4 import BeautifulSoup
from influxdb_client import InfluxDBClient

# Scraping the website
url = "https://fam-lange.de/wetter.php"
response = requests.get(url)
soup = BeautifulSoup(response.content, "html.parser")

# Find the div containing the rain data
rain_card = soup.find("div", class_="card-header", string="Regen")

if rain_card:
    # Find the next sibling div (which contains the rain value)
    rain_value_element = rain_card.find_next_sibling("div").find("h5")
    rain_value = rain_value_element.text.strip()
    # Extract only the numeric value before "mm"
    match = re.search(r"(\d+\.?\d*)\s*mm", rain_value)
    if match:
        rain_value = match.group(1)
        print(f"Rain value (last 24h): {rain_value} mm")
    else:
        print("Rain value not found.")
else:
    print("Rain card not found on the website.")
    exit()

# Writing to InfluxDB
#rain_value = 15
bucket = "wetter"
org = "org"
token = os.environ.get("INFLUXDB_TOKEN")
url = "https://influxdb.ioui.eu"
client = InfluxDBClient(url=url, token=token, org=org, verify_ssl=False)
write_api = client.write_api()

data = f"rain value={rain_value}"
write_api.write(bucket=bucket, org=org, record=data)

print(f"Rain value {rain_value} written to InfluxDB.")

write_api.close()
client.close()

