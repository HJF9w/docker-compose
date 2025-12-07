import requests
import re
import os
from bs4 import BeautifulSoup
from influxdb_client import InfluxDBClient

# scrape
url = "https://www.iqair.com/de/germany/saxony/dresden/bergstr" 

response = requests.get(url)
soup = BeautifulSoup(response.content, "html.parser")

# Find the row with "PM10"
row_pm10 = soup.find("td", string=" PM10 ")

if row_pm10:
    value_span = row_pm10.find_next("span", class_="pollutant-concentration-value")
    value = value_span.get_text()
    print("The value for PM10 is:", value)
else:
    print("PM10 value not found on the page.")

# Writing to InfluxDB
#value = 15
bucket = "wetter"
org = "org"
token = os.environ.get("INFLUXDB_TOKEN")
url = "https://influxdb.home.arpa"
client = InfluxDBClient(url=url, token=token, org=org, verify_ssl=False)
write_api = client.write_api()

data = f"suedvorstadt-pm10 value={value}"
write_api.write(bucket=bucket, org=org, record=data)

print(f"suedvorstadt-pm10 value {value} written to InfluxDB.")

write_api.close()
client.close()

