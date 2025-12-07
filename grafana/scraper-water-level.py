import requests
import re
import os
from bs4 import BeautifulSoup
from influxdb_client import InfluxDBClient

# Scraping the website
url = "https://www.pegelonline.wsv.de/gast/stammdaten?pegelnr=501060"
response = requests.get(url)
soup = BeautifulSoup(response.content, "html.parser")
water_level_element = soup.find("td", string="Wasserstand [cm]")
if water_level_element:
    water_level_value = water_level_element.find_next_sibling("td").text.strip()
    water_level_value = re.sub(r'[^\d.-]', '', water_level_value)  # Remove non-digit, non-dot, non-minus characters
else:
    print("water_level value not found on the website.")
    exit()

# Writing to InfluxDB
#water_level_value = 15
bucket = "wetter"
org = "org"
token = os.environ.get("INFLUXDB_TOKEN")
url = "https://influxdb.home.arpa"
client = InfluxDBClient(url=url, token=token, org=org, verify_ssl=False)
write_api = client.write_api()

data = f"water_level value={water_level_value}"
write_api.write(bucket=bucket, org=org, record=data)

print(f"water_level value {water_level_value} written to InfluxDB.")

write_api.close()
client.close()

