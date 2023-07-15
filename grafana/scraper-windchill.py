import requests
import re
import os
from bs4 import BeautifulSoup
from influxdb_client import InfluxDBClient

# Scraping the website
url = "https://fam-lange.de/wetter.php"
response = requests.get(url)
soup = BeautifulSoup(response.content, "html.parser")
windchill_element = soup.find("td", text="Windchill (gefühlte Temp.)")

if windchill_element:
    windchill_value = windchill_element.find_next_sibling("td").text.strip()
    windchill_value = re.sub(r'[^\d.-]', '', windchill_value)  # Remove non-digit, non-dot, non-minus characters
else:
    print("WindChill value not found on the website.")
    exit()

# Writing to InfluxDB
#windchill_value = 15
bucket = "wetter"
org = "org"
token = os.environ.get("INFLUXDB_TOKEN")
url = "https://influxdb.home.arpa"
client = InfluxDBClient(url=url, token=token, org=org, verify_ssl=False)
write_api = client.write_api()

data = f"windchill value={windchill_value}"
write_api.write(bucket=bucket, org=org, record=data)

print(f"WindChill value {windchill_value} written to InfluxDB.")

write_api.close()
client.close()

