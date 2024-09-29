import requests
import re
import os
from bs4 import BeautifulSoup
from influxdb_client import InfluxDBClient

# Scraping the website
url = "https://fam-lange.de/wetter.php"
response = requests.get(url)
soup = BeautifulSoup(response.content, "html.parser")

# Find the card with the "Taupunkt" header
dewpoint_card = soup.find("div", class_="card-header", string="Taupunkt")

if dewpoint_card:
    # Find the next sibling with the class "card-body" that contains the dewpoint value
    dewpoint_value = dewpoint_card.find_next_sibling("div").find("h5", class_="card-title").text.strip()
    # Clean up the dewpoint value by removing non-digit characters, except for the dot and minus
    dewpoint_value = re.sub(r'[^\d.-]', '', dewpoint_value)
    print(f"DewPoint Value: {dewpoint_value}°C")
else:
    print("DewPoint value not found on the website.")
    exit();

# Writing to InfluxDB
#dewpoint_value = 15
bucket = "wetter"
org = "org"
token = os.environ.get("INFLUXDB_TOKEN")
url = "https://influxdb.ioui.eu"
client = InfluxDBClient(url=url, token=token, org=org, verify_ssl=False)
write_api = client.write_api()

data = f"dewpoint value={dewpoint_value}"
write_api.write(bucket=bucket, org=org, record=data)

print(f"DewPoint value {dewpoint_value} written to InfluxDB.")

write_api.close()
client.close()

