import requests
import re
import os
from bs4 import BeautifulSoup
from influxdb_client import InfluxDBClient

# Scraping the website
url = "https://fam-lange.de/wetter.php"
response = requests.get(url)
soup = BeautifulSoup(response.content, "html.parser")

# Find the 'Luftdruck (rel. NN)' card header
airpressure_card = soup.find("div", class_="card-header", string="Luftdruck (rel. NN)")

if airpressure_card:
    # Find the corresponding <h5> tag in the card body
    airpressure_value = airpressure_card.find_next("div", class_="card-body").find("h5").text.strip()
    airpressure_value = re.sub(r'[^\d.-]', '', airpressure_value)  # Remove non-digit, non-dot, non-minus characters
    print(f"Air pressure: {airpressure_value} hPa")
else:
    print("AirPressure value not found on the website.")
    exit();

# Writing to InfluxDB
bucket = "wetter"
org = "org"
token = os.environ.get("INFLUXDB_TOKEN")
url = "https://influxdb.ioui.eu"
client = InfluxDBClient(url=url, token=token, org=org, verify_ssl=False)
write_api = client.write_api()

data = f"airpressure value={airpressure_value}"
write_api.write(bucket=bucket, org=org, record=data)

print(f"AirPressure value {airpressure_value} written to InfluxDB.")

write_api.close()
client.close()

