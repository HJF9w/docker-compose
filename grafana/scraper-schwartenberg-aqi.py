import requests
import re
import os
from bs4 import BeautifulSoup
from influxdb_client import InfluxDBClient

# scrape
# URL of the website
url = "https://www.iqair.com/de/germany/saxony/schwartenberg/schwartenberg-s"

# Send a GET request to the URL
response = requests.get(url)

# Parse the HTML content using BeautifulSoup
soup = BeautifulSoup(response.content, "html.parser")

# Find the AQI value element
aqi_value_element = soup.find("p", class_="aqi-value__value")

# Extract the text of the AQI value element
value = aqi_value_element.get_text()

# Writing to InfluxDB
#value = 15
bucket = "wetter"
org = "org"
token = os.environ.get("INFLUXDB_TOKEN")
url = "https://influxdb.home.arpa"
client = InfluxDBClient(url=url, token=token, org=org, verify_ssl=False)
write_api = client.write_api()

data = f"schwartenberg-aqi value={value}"
write_api.write(bucket=bucket, org=org, record=data)

print(f"schwartenberg-aqi value {value} written to InfluxDB.")

write_api.close()
client.close()

