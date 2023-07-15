import requests
import re
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
    print("Windspeed value not found on the website.")
    exit()

print("is: {windspeed_value}")
# Writing to InfluxDB
#windspeed_value = 15
bucket = "db0"
org = "local"
token = "_iAgV7QQcvZlyoOuQI0oHupuboMZPctoZ9ZSjEaR7YO59bKZqmR6XOk-MEKjaWtB_TsYtTiH_vcQNlqi4o-gew=="
url = "http://localhost:8086"
client = InfluxDBClient(url=url, token=token, org=org)
write_api = client.write_api()

data = f"windspeed value={windspeed_value}"
write_api.write(bucket=bucket, org=org, record=data)

print(f"Windspeed value {windspeed_value} written to InfluxDB.")

write_api.close()
client.close()

