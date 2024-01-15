import requests
import re
import os
from bs4 import BeautifulSoup
from influxdb_client import InfluxDBClient

# scrape
url = "https://www.iqair.com/de/germany/saxony/schwartenberg/schwartenberg-s"

response = requests.get(url)
soup = BeautifulSoup(response.content, "html.parser")

# Find the row with "so2"
row_so2 = soup.find("td", string=" SO2 ")

if row_so2:
    value_span = row_so2.find_next("span", class_="pollutant-concentration-value")
    value = value_span.get_text()
    print("The value for so2 is:", value)
else:
    print("so2 value not found on the page.")

# Writing to InfluxDB
#value = 15
bucket = "wetter"
org = "org"
token = os.environ.get("INFLUXDB_TOKEN")
url = "https://influxdb.home.arpa"
client = InfluxDBClient(url=url, token=token, org=org, verify_ssl=False)
write_api = client.write_api()

data = f"schwartenberg-so2 value={value}"
write_api.write(bucket=bucket, org=org, record=data)

print(f"schwartenberg-so2 value {value} written to InfluxDB.")

write_api.close()
client.close()

