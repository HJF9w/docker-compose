import requests
import re
import os
from bs4 import BeautifulSoup
from influxdb_client import InfluxDBClient

# Scraping the website
url = "https://fam-lange.de/wetter.php"
response = requests.get(url)
soup = BeautifulSoup(response.content, "html.parser")
windspeed_element = soup.find("td", text="Windgeschwindigkeit")

if windspeed_element:
    windspeed_value = windspeed_element.find_next_sibling("td").text.strip()
    windspeed_value = re.sub(r'[^\d.-]', '', windspeed_value)  # Remove non-digit, non-dot, non-minus characters
else:
    print("WindSpeed value not found on the website.")
    exit()

# Writing to InfluxDB
#windspeed_value = 15
bucket = "wetter"
org = "org"
token = os.environ.get("INFLUXDB_TOKEN")
url = "https://influxdb.home.arpa"
client = InfluxDBClient(url=url, token=token, org=org, verify_ssl=False)
write_api = client.write_api()

data = f"windspeed value={windspeed_value}"
write_api.write(bucket=bucket, org=org, record=data)

print(f"WindSpeed value {windspeed_value} written to InfluxDB.")

write_api.close()
client.close()

