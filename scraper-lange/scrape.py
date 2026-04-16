#!/usr/bin/env python3
import argparse
import re
import sys
import time
import smtplib
import csv
import zipfile
import io
from email.message import EmailMessage
from datetime import datetime, date, time as dt_time, timezone

import requests
from bs4 import BeautifulSoup
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

def send_error_email(args, subject, body):
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = args.email_from
    msg['To'] = args.email_to
    msg.set_content(body)
    try:
        with smtplib.SMTP(args.smtp_host, args.smtp_port) as smtp:
            if args.smtp_use_tls:
                smtp.starttls()
            if args.smtp_user and args.smtp_pass:
                smtp.login(args.smtp_user, args.smtp_pass)
            smtp.send_message(msg)
    except Exception as e:
        print(f"Failed to send error email: {e}", file=sys.stderr)

def run_with_retries(args, subject, func, default=None, body_prefix=""):
    for i in range(3):
        try:
            return func()
        except Exception as e:
            if i < 2:
                time.sleep(5)
            else:
                send_error_email(args, subject, f"{body_prefix}{e}")
                return default

def fetch_soup(session, url):
    resp = session.get(url, timeout=10)
    resp.raise_for_status()
    return BeautifulSoup(resp.content, "html.parser")

def parse_fam_lange(soup):
    data = {}
    mappings = {
        "temperature":    "Temperatur",
        "dewpoint":       "Taupunkt",
        "humidity":       "Luftfeuchte",
        "windspeed":      "Windgeschwindigkeit",
        "winddirection":  "Windrichtung",
        "windgust":       "max. Windboe",
        "airpressure":    "Luftdruck (rel. NN)",
        "rain":           "Regen",
        "windchill":      "Windchill",
    }
    for key, header in mappings.items():
        card = soup.find("div", class_="card-header", string=header)
        if not card:
            raise ValueError(f"'{header}' card not found")
        body = card.find_next_sibling("div", class_="card-body")
        if not body:
            raise ValueError(f"No body for '{header}' card")
        txt = body.find("h5", class_="card-title") or body.find("h5")
        if not txt:
            raise ValueError(f"No <h5> in '{header}' card body")
        val = txt.text.strip()
        if key == "rain":
            m = re.search(r"(\d+\.?\d*)\s*mm", val)
            if not m:
                raise ValueError("Rain value not found")
            val = m.group(1)
        else:
            val = re.sub(r'[^\d\.-]', '', val).rstrip('-')
        data[key] = val
    return data

def parse_pegelonline(soup):
    data = {}
    out_el = soup.find("td", string=re.compile(r"Abfluss"))
    if not out_el:
        raise ValueError("Abfluss element not found")
    data["water_outflow"] = re.sub(r'[^\d\.-]', '', out_el.find_next_sibling("td").text).rstrip('-')

    lvl_el = soup.find("td", string=re.compile(r"Wasserstand"))
    if not lvl_el:
        raise ValueError("Wasserstand element not found")
    data["water_level"] = re.sub(r'[^\d\.-]', '', lvl_el.find_next_sibling("td").text).rstrip('-')

    return data

def parse_solar(soup):
    data = {}
    section = soup.find("section", id="content1-1y")
    if not section:
        raise ValueError("Solar section #content1-1y not found")
    container = section.find("div", class_="mbr-text")
    if not container:
        raise ValueError("Solar container in section not found")
    ps = container.find_all("p")
    if len(ps) < 2:
        raise ValueError("Expected two <p> tags in solar data block")
    data_p = ps[1]
    strongs = data_p.find_all("strong")
    if len(strongs) < 2:
        raise ValueError("Expected two <strong> tags (power & energy)")
    power_raw  = strongs[0].get_text()
    energy_raw = strongs[1].get_text()
    data["power"]       = re.sub(r'[^\d\.]', '', power_raw)
    data["totalenergy"] = re.sub(r'[^\d\.]', '', energy_raw)
    return data

def parse_neon_ext_temp(text):
    m = re.match(r"^extTempSensor=(-?\d+\.?\d*)$", text.strip())
    if not m:
        raise ValueError(f"Unexpected sensor response: {text[:100]}")
    return m.group(1)

def parse_neon_cpu_temp(text):
    m = re.match(r"^cpuTemp=(-?\d+\.?\d*)$", text.strip())
    if not m:
        raise ValueError(f"Unexpected sensor response: {text[:100]}")
    return m.group(1)

def write_metric(write_api, bucket, org, key, value, timestamp=None):
    point = Point(key).field("value", float(value))
    if timestamp:
        point = point.time(timestamp)
    write_api.write(bucket=bucket, org=org, record=point)


# --- DWD WEATHER FUNCTIONS ---

def fetch_dwd_zip(session, url):
    # Bumped timeout to 60s for the historical file
    resp = session.get(url, timeout=60)
    resp.raise_for_status()
    return zipfile.ZipFile(io.BytesIO(resp.content))

def process_dwd_zip(z, write_api, bucket, org, station_id):
    txt_filename = None
    for name in z.namelist():
        if name.startswith("produkt_") and name.endswith(".txt"):
            txt_filename = name
            break
            
    if not txt_filename:
        file_list = ", ".join(z.namelist())
        raise ValueError(f"No 'produkt_*.txt' data file found in DWD zip. Files present: {file_list}")
        
    with z.open(txt_filename) as f:
        content = f.read().decode('latin1')
        
    reader = csv.DictReader(io.StringIO(content), delimiter=';')
    
    # Mapping DWD KL columns to field names
    # TMK: Mean Temp, UPM: Humidity, NM: Cloudiness, FM: Wind Speed, 
    # FX: Wind Gust, PM: Pressure, RSK: Rain, SDK: Sunshine
    field_mapping = {
        'TMK': 'temperature',
        'UPM': 'humidity',
        'NM':  'cloudiness',
        'FM':  'wind_speed',
        'FX':  'wind_gust',
        'PM':  'pressure',
        'RSK': 'rain',
        'SDK': 'sunshine'
    }
    
    points = []
    processed_count = 0
    
    for row in reader:
        try:
            # Clean whitespaces in keys and values
            row = {k.strip(): v.strip() for k, v in row.items() if k}
            
            date_str = row.get('MESS_DATUM')
            if not date_str:
                continue
                
            dt = datetime.strptime(date_str, "%Y%m%d").replace(tzinfo=timezone.utc)
            p = Point("dwd_climate").tag("station", station_id).tag("source", "opendata.dwd.de").time(dt)
            
            has_data = False
            for dwd_key, field_name in field_mapping.items():
                val_str = row.get(dwd_key)
                if val_str and val_str != '-999':
                    p.field(field_name, float(val_str))
                    has_data = True
            
            if has_data:
                points.append(p)
                processed_count += 1
            
            # Write chunks and log progress
            if len(points) >= 5000:
                write_api.write(bucket=bucket, org=org, record=points)
                print(f"Processed {processed_count} rows...")
                points = []
        except Exception:
            # Skip bad rows
            continue
            
    if points:
        write_api.write(bucket=bucket, org=org, record=points)
        
    return processed_count

def check_history_loaded(query_api, bucket, station_id):
    # Query across all time to check for flag
    # Using 'dwd_system_kl' to distinguish from previous precip-only flag if any
    query = f'''
    from(bucket: "{bucket}")
      |> range(start: 0)
      |> filter(fn: (r) => r._measurement == "dwd_system" and r.station == "{station_id}" and r._field == "history_loaded_kl")
      |> last()
    '''
    tables = query_api.query(query)
    return len(tables) > 0

def mark_history_loaded(write_api, bucket, org, station_id):
    p = Point("dwd_system").tag("station", station_id).field("history_loaded_kl", True).time(datetime.now(timezone.utc))
    write_api.write(bucket=bucket, org=org, record=p)

def get_dwd_historical_url(session, station_id):
    base_url = "https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/daily/kl/historical/"
    resp = session.get(base_url, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "html.parser")
    for a in soup.find_all('a'):
        href = a.get('href')
        if href and f"_{station_id}_" in href and href.endswith("_hist.zip"):
            return base_url + href
    raise ValueError(f"Historical KL zip for station {station_id} not found.")

def scrape_dwd(args, session, query_api, write_api):
    station_id = args.dwd_station_id
    
    # 1. Historical Load
    hist_loaded = run_with_retries(args, "Influx Query Error", 
                                   lambda: check_history_loaded(query_api, args.influx_bucket, station_id), 
                                   default=True)
    if not hist_loaded:
        print(f"[{datetime.now().isoformat()}] Flag not found. Starting historical KL import for station {station_id}...")
        hist_url = run_with_retries(args, "DWD Historical URL Error", 
                                    lambda: get_dwd_historical_url(session, station_id))
        if hist_url:
            def load_hist():
                z = fetch_dwd_zip(session, hist_url)
                count = process_dwd_zip(z, write_api, args.influx_bucket, args.influx_org, station_id)
                mark_history_loaded(write_api, args.influx_bucket, args.influx_org, station_id)
                return count
            count = run_with_retries(args, "DWD Historical Data Error", load_hist)
            if count is not None:
                print(f"Historical DWD KL data successfully imported ({count} valid records).")
            
    # 2. Daily Recent Data Update
    DWD_LAST_FETCH_FILE = "/tmp/dwd_last_fetch_kl.txt"
    today = date.today().isoformat()
    try:
        with open(DWD_LAST_FETCH_FILE, "r") as f:
            if f.read().strip() == today:
                return 
    except FileNotFoundError:
        pass

    print(f"[{datetime.now().isoformat()}] Fetching recent DWD KL data...")
    recent_url = f"https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/daily/kl/recent/tageswerte_KL_{station_id}_akt.zip"
    
    def load_recent():
        z = fetch_dwd_zip(session, recent_url)
        return process_dwd_zip(z, write_api, args.influx_bucket, args.influx_org, station_id)
    
    count = run_with_retries(args, "DWD Recent Data Error", load_recent)
    if count is not None:
        print(f"Recent DWD KL data updated ({count} valid records).")
        try:
            with open(DWD_LAST_FETCH_FILE, "w") as f:
                f.write(today)
        except Exception as e:
            print(f"Warning: could not write DWD state: {e}", file=sys.stderr)

# --- END DWD FUNCTIONS ---

def main():
    p = argparse.ArgumentParser()
    # InfluxDB args
    p.add_argument("--influx-url",    required=True)
    p.add_argument("--influx-token",  required=True)
    p.add_argument("--influx-org",    required=True)
    p.add_argument("--influx-bucket", required=True)
    # SMTP args
    p.add_argument("--smtp-host",    required=True)
    p.add_argument("--smtp-port",    type=int, default=587)
    p.add_argument("--smtp-use-tls", action="store_true")
    p.add_argument("--smtp-user")
    p.add_argument("--smtp-pass")
    p.add_argument("--email-from",   required=True)
    p.add_argument("--email-to",     required=True)
    p.add_argument("--neon-ext-sensor-url")
    p.add_argument("--neon-cpu-sensor-url")
    p.add_argument("--dwd-station-id", default="00991", help="DWD station ID")
    args = p.parse_args()

    client = InfluxDBClient(
        url=args.influx_url,
        token=args.influx_token,
        org=args.influx_org
    )
    query_api = client.query_api()
    write_api = client.write_api(write_options=SYNCHRONOUS)

    sess_wx   = requests.Session()
    sess_peg  = requests.Session()
    sess_sol  = requests.Session()

    fam_data = run_with_retries(args, "Fam-Lange Weather Error",
                                lambda: parse_fam_lange(fetch_soup(sess_wx, "https://fam-lange.de/wetter.php")),
                                default={})
    peg_data = run_with_retries(args, "PegelOnline Error",
                                lambda: parse_pegelonline(fetch_soup(sess_peg, "https://www.pegelonline.wsv.de/gast/stammdaten?pegelnr=501060")),
                                default={})
    solar_data = run_with_retries(args, "Solar Scrape Error",
                                  lambda: parse_solar(fetch_soup(sess_sol, "https://fam-lange.de/solar.php")),
                                  default={})

    if args.neon_ext_sensor_url:
        def scrape_neon_ext():
            resp = requests.get(args.neon_ext_sensor_url, timeout=10)
            resp.raise_for_status()
            sensor_val = parse_neon_ext_temp(resp.text)
            write_metric(write_api, args.influx_bucket, args.influx_org, "neonExtTempSensor", sensor_val)
        run_with_retries(args, "Sensor Scrape Error", scrape_neon_ext)

    if args.neon_cpu_sensor_url:
        def scrape_neon_cpu():
            resp = requests.get(args.neon_cpu_sensor_url, timeout=10)
            resp.raise_for_status()
            sensor_val = parse_neon_cpu_temp(resp.text)
            write_metric(write_api, args.influx_bucket, args.influx_org, "neonCPUTempSensor", sensor_val)
        run_with_retries(args, "Sensor Scrape Error", scrape_neon_cpu)

    # DWD Daily Rain Scrape
    scrape_dwd(args, sess_wx, query_api, write_api)

    for k, v in {**fam_data, **peg_data, **solar_data}.items():
        if k == "totalenergy": continue
        run_with_retries(args, "InfluxDB Write Error",
                         lambda: write_metric(write_api, args.influx_bucket, args.influx_org, k, v),
                         body_prefix=f"{k}={v}: ")

    if "totalenergy" in solar_data:
        noon = datetime.combine(date.today(), dt_time(12, 0, 0), tzinfo=timezone.utc)
        run_with_retries(args, "InfluxDB Write Error",
                         lambda: write_metric(write_api, args.influx_bucket, args.influx_org, "totalenergy", solar_data["totalenergy"], timestamp=noon),
                         body_prefix=f"totalenergy={solar_data['totalenergy']}: ")

    write_api.close()
    client.close()

if __name__ == "__main__":
    main()
