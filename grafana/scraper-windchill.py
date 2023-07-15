import requests
import re
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

print("is: {windchill_value}")
# Writing to InfluxDB
#windchill_value = 15
bucket = "db0"
org = "local"
token = "_iAgV7QQcvZlyoOuQI0oHupuboMZPctoZ9ZSjEaR7YO59bKZqmR6XOk-MEKjaWtB_TsYtTiH_vcQNlqi4o-gew=="
url = "http://localhost:8086"
client = InfluxDBClient(url=url, token=token, org=org)
write_api = client.write_api()

data = f"windchill value={windchill_value}"
write_api.write(bucket=bucket, org=org, record=data)

print(f"WindChill value {windchill_value} written to InfluxDB.")

write_api.close()
client.close()

