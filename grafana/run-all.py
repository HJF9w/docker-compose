import subprocess
import requests
import re
import os
from bs4 import BeautifulSoup
from influxdb_client import InfluxDBClient

# Get the directory where the script is located
script_dir = os.path.dirname(os.path.abspath(__file__))

# Get the name of the script itself
script_name = os.path.basename(__file__)

# Iterate over all files in the directory
for filename in os.listdir(script_dir):
    # Check if the file is a Python script and not the script itself
    if filename.endswith('.py') and filename != script_name:
        # Get the full path to the file
        file_path = os.path.join(script_dir, filename)
        
        print(f"Running {filename}")
        # Execute the Python script
        subprocess.run(['python', file_path], check=True)

print("All scripts executed.")
