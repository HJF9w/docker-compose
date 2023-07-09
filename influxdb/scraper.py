import requests
from bs4 import BeautifulSoup
from influxdb import InfluxDBClient

# URL of the website to scrape
url = 'https://fam-lange.de/wetter.php'

# Connect to InfluxDB
client = InfluxDBClient(host='localhost', port=8086, username='admin', password='pw4admin', database='db0')

# Make a GET request to the website
response = requests.get(url)

# Parse the HTML content
soup = BeautifulSoup(response.content, 'html.parser')

# Find the temperature value
temperature_element = soup.find('td', text='Temperatur')
temperature_value = temperature_element.find_next('td').get_text(strip=True)

# Remove non-breaking space and degree symbols
temperature_value = temperature_value.replace('\xa0', '').replace('°C', '')

# Create a data point for InfluxDB
data = [
    {
        "measurement": "temperature",
        "fields": {
            "value": float(temperature_value)
        }
    }
]

# Write the data point to InfluxDB
client.write_points(data)

# Close the InfluxDB connection
client.close()

