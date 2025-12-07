import requests
import re
import os
from bs4 import BeautifulSoup
from influxdb_client import InfluxDBClient

# Scraping the website
url = "https://www.pegelonline.wsv.de/gast/stammdaten?pegelnr=501060"
response = requests.get(url)
soup = BeautifulSoup(response.content, "html.parser")
water_outflow_element = soup.find("td", string="Abfluss [mÂ³/s]")
if water_outflow_element:
    water_outflow_value = water_outflow_element.find_next_sibling("td").text.strip()
    water_outflow_value = re.sub(r'[^\d.-]', '', water_outflow_value)  # Remove non-digit, non-dot, non-minus characters
else:
    print("water_outflow value not found on the website.")
    exit()

# Writing to InfluxDB
#water_outflow_value = 15
bucket = "wetter"
org = "org"
token = os.environ.get("INFLUXDB_TOKEN")
url = "https://influxdb.home.arpa"
client = InfluxDBClient(url=url, token=token, org=org, verify_ssl=False)
write_api = client.write_api()

data = f"water_outflow value={water_outflow_value}"
write_api.write(bucket=bucket, org=org, record=data)

print(f"water_outflow value {water_outflow_value} written to InfluxDB.")

write_api.close()
client.close()

