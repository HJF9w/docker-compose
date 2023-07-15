import requests
import re
from bs4 import BeautifulSoup
from influxdb_client import InfluxDBClient

# Scraping the website
url = "https://fam-lange.de/wetter.php"
response = requests.get(url)
soup = BeautifulSoup(response.content, "html.parser")
airpressure_element = soup.find("td", text="Luftdruck (rel. NN)")

if airpressure_element:
    airpressure_value = airpressure_element.find_next_sibling("td").text.strip()
    airpressure_value = re.sub(r'[^\d.-]', '', airpressure_value)  # Remove non-digit, non-dot, non-minus characters
else:
    print("AirPressure value not found on the website.")
    exit()

print("is: {airpressure_value}")
# Writing to InfluxDB
#airpressure_value = 15
bucket = "db0"
org = "local"
token = "_iAgV7QQcvZlyoOuQI0oHupuboMZPctoZ9ZSjEaR7YO59bKZqmR6XOk-MEKjaWtB_TsYtTiH_vcQNlqi4o-gew=="
url = "http://localhost:8086"
client = InfluxDBClient(url=url, token=token, org=org)
write_api = client.write_api()

data = f"airpressure value={airpressure_value}"
write_api.write(bucket=bucket, org=org, record=data)

print(f"AirPressure value {airpressure_value} written to InfluxDB.")

write_api.close()
client.close()

