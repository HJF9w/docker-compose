import requests
import re
import os
from bs4 import BeautifulSoup
from influxdb_client import InfluxDBClient

# Scraping the website
url = "https://fam-lange.de/wetter.php"
response = requests.get(url)
soup = BeautifulSoup(response.content, "html.parser")

# Find the card with the header 'Windgeschwindigkeit'
windspeed_card = soup.find("div", class_="card-header", string="Windgeschwindigkeit")

if windspeed_card:
    # The value is in the next sibling card-body
    windspeed_value = windspeed_card.find_next("div", class_="card-body").find("h5", class_="card-title").text.strip()
    # Extract numeric value (windspeed)
    windspeed_value = re.sub(r'[^\d.-]', '', windspeed_value)  # Remove non-digit, non-dot, non-minus characters
    print(f"Wind Speed: {windspeed_value} Kmh")
else:
    print("Wind Speed value not found on the website.")
    exit()

# Writing to InfluxDB
#windspeed_value = 15
bucket = "wetter"
org = "org"
token = os.environ.get("INFLUXDB_TOKEN")
url = "https://influxdb.ioui.eu"
client = InfluxDBClient(url=url, token=token, org=org, verify_ssl=False)
write_api = client.write_api()

data = f"windspeed value={windspeed_value}"
write_api.write(bucket=bucket, org=org, record=data)

print(f"WindSpeed value {windspeed_value} written to InfluxDB.")

write_api.close()
client.close()

