import requests
import re
import os
from bs4 import BeautifulSoup
from influxdb_client import InfluxDBClient

# Scraping the website
url = "https://fam-lange.de/wetter.php"
response = requests.get(url)
soup = BeautifulSoup(response.content, "html.parser")
dewpoint_element = soup.find("td", string="Taupunkt")

if dewpoint_element:
    dewpoint_value = dewpoint_element.find_next_sibling("td").text.strip()
    dewpoint_value = re.sub(r'[^\d.-]', '', dewpoint_value)  # Remove non-digit, non-dot, non-minus characters
else:
    print("DewPoint value not found on the website.")
    exit()

# Writing to InfluxDB
#dewpoint_value = 15
bucket = "wetter"
org = "org"
token = os.environ.get("INFLUXDB_TOKEN")
url = "https://influxdb.home.arpa"
client = InfluxDBClient(url=url, token=token, org=org, verify_ssl=False)
write_api = client.write_api()

data = f"dewpoint value={dewpoint_value}"
write_api.write(bucket=bucket, org=org, record=data)

print(f"DewPoint value {dewpoint_value} written to InfluxDB.")

write_api.close()
client.close()

