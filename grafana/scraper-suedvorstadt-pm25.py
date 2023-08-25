import requests
import re
import os
from bs4 import BeautifulSoup
from influxdb_client import InfluxDBClient

# scrape
url = "https://www.iqair.com/de/germany/saxony/dresden/bergstr" 

response = requests.get(url)
soup = BeautifulSoup(response.content, "html.parser")

# Find the row with "PM25"
row_pm25 = soup.find("td", string=" PM2.5 ")

if row_pm25:
    value_span = row_pm25.find_next("span", class_="pollutant-concentration-value")
    value = value_span.get_text()
    print("The value for PM25 is:", value)
else:
    print("PM25 value not found on the page.")

# Writing to InfluxDB
#value = 15
bucket = "wetter"
org = "org"
token = os.environ.get("INFLUXDB_TOKEN")
url = "https://influxdb.home.arpa"
client = InfluxDBClient(url=url, token=token, org=org, verify_ssl=False)
write_api = client.write_api()

data = f"suedvorstadt-pm25 value={value}"
write_api.write(bucket=bucket, org=org, record=data)

print(f"suedvorstadt-pm25 value {value} written to InfluxDB.")

write_api.close()
client.close()

