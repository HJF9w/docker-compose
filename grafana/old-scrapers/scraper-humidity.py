import requests
import re
import os
from bs4 import BeautifulSoup
from influxdb_client import InfluxDBClient

# Scraping the website
url = "https://fam-lange.de/wetter.php"
response = requests.get(url)
soup = BeautifulSoup(response.content, "html.parser")

# Find the card with the header 'Luftfeuchte'
humidity_card = soup.find("div", class_="card-header", string="Luftfeuchte")

if humidity_card:
    # The value is in the next sibling card-body
    humidity_value = humidity_card.find_next("div", class_="card-body").find("h5", class_="card-title").text.strip()
    # Extract numeric value (humidity)
    humidity_value = re.sub(r'[^\d.-]', '', humidity_value)  # Remove non-digit, non-dot, non-minus characters
    print(f"Humidity: {humidity_value}%")
else:
    print("Humidity value not found on the website.")
    exit()

# Writing to InfluxDB
#humidity_value = 15
bucket = "wetter"
org = "org"
token = os.environ.get("INFLUXDB_TOKEN")
url = "https://influxdb.ioui.eu"
client = InfluxDBClient(url=url, token=token, org=org, verify_ssl=False)
write_api = client.write_api()

data = f"humidity value={humidity_value}"
write_api.write(bucket=bucket, org=org, record=data)

print(f"Humidity value {humidity_value} written to InfluxDB.")

write_api.close()
client.close()

