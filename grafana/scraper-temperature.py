import requests
import re
import os
from bs4 import BeautifulSoup
from influxdb_client import InfluxDBClient

# Scraping the website
url = "https://fam-lange.de/wetter.php"
response = requests.get(url)
soup = BeautifulSoup(response.content, "html.parser")
temperature_element = soup.find("td", string="Temperatur")

if temperature_element:
    temperature_value = temperature_element.find_next_sibling("td").text.strip()
    temperature_value = re.sub(r'[^\d.-]', '', temperature_value)  # Remove non-digit, non-dot, non-minus characters
else:
    print("Temperature value not found on the website.")
    exit()

# Writing to InfluxDB
#temperature_value = 15
bucket = "wetter"
org = "org"
token = os.environ.get("INFLUXDB_TOKEN")
url = "https://influxdb.home.arpa"
client = InfluxDBClient(url=url, token=token, org=org, verify_ssl=False)
write_api = client.write_api()

data = f"temperature value={temperature_value}"
write_api.write(bucket=bucket, org=org, record=data)

print(f"Temperature value {temperature_value} written to InfluxDB.")

write_api.close()
client.close()

