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
import psycopg
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS


def log_message(level, message):
    print(f"[{datetime.now().isoformat()}] [{level}] {message}")

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
                log_message("WARN", f"{subject} attempt {i + 1}/3 failed: {e}. Retrying in 5s.")
                time.sleep(5)
            else:
                log_message("ERROR", f"{subject} failed after 3 attempts: {e}")
                send_error_email(args, subject, f"{body_prefix}{e}")
                return default


def run_with_db_retries(args, conn, subject, func, default=None, body_prefix=""):
    for i in range(3):
        try:
            return func()
        except Exception as e:
            try:
                conn.rollback()
            except Exception as rollback_error:
                print(f"PostgreSQL rollback failed: {rollback_error}", file=sys.stderr)
            if i < 2:
                log_message("WARN", f"{subject} attempt {i + 1}/3 failed: {e}. Rolled back transaction and retrying in 5s.")
                time.sleep(5)
            else:
                log_message("ERROR", f"{subject} failed after 3 attempts: {e}")
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
    # Bumped timeout to 60s for historical files
    resp = session.get(url, timeout=60)
    resp.raise_for_status()
    return zipfile.ZipFile(io.BytesIO(resp.content))


def dwd_recent_index_contains_file(session, resolution, category, filename):
    index_url = (
        "https://opendata.dwd.de/climate_environment/CDC/observations_germany/"
        f"climate/{resolution}/{category}/recent/"
    )
    resp = session.get(index_url, timeout=30)
    resp.raise_for_status()
    exists = filename in resp.text
    log_message("INFO", f"DWD index check {resolution}/{category}: {'found' if exists else 'missing'} {filename}")
    return exists

def process_dwd_zip_kl(z, conn, station_id):
    """Processes daily climate (KL) data and upserts it into PostgreSQL."""
    txt_filename = next((n for n in z.namelist() if n.startswith("produkt_") and n.endswith(".txt")), None)
    if not txt_filename:
        return 0
    with z.open(txt_filename) as f:
        content = f.read().decode('latin1')
    reader = csv.DictReader(io.StringIO(content), delimiter=';')
    field_mapping = {
        'TMK': 'temperature', 'UPM': 'humidity', 'NM': 'cloudiness',
        'FM': 'wind_speed', 'FX': 'wind_gust', 'PM': 'pressure',
        'RSK': 'rain', 'SDK': 'sunshine'
    }
    observations = []
    count = 0
    for row in reader:
        row = {k.strip(): v.strip() for k, v in row.items() if k}
        dt_str = row.get('MESS_DATUM')
        if not dt_str:
            continue
        dt = datetime.strptime(dt_str, "%Y%m%d").replace(tzinfo=timezone.utc)
        metrics = build_dwd_metrics(row, field_mapping)
        if metrics:
            observations.append(build_dwd_observation(station_id, dt, 'daily', 'kl', metrics))
            count += 1
        if len(observations) >= 5000:
            upsert_dwd_observations(conn, observations)
            observations = []
    if observations:
        upsert_dwd_observations(conn, observations)
    return count


def parse_dwd_float(value):
    if value is None:
        return None
    value = value.strip().replace(',', '.')
    if not value or value in ('-999', '-999.0'):
        return None
    return float(value)


def build_dwd_metrics(row, field_mapping):
    metrics = {}
    for dwd_key, field_name in field_mapping.items():
        value = parse_dwd_float(row.get(dwd_key))
        if value is not None:
            metrics[field_name] = value
    return metrics


def build_dwd_observation(station_id, ts_utc, resolution, source, metrics):
    observation = {
        'station_id': station_id,
        'ts_utc': ts_utc,
        'resolution': resolution,
        'source': source,
        'temperature': None,
        'humidity': None,
        'cloudiness': None,
        'wind_speed': None,
        'wind_gust': None,
        'wind_direction': None,
        'pressure': None,
        'rain': None,
        'rain_rate_10min': None,
        'sunshine': None,
    }
    observation.update(metrics)
    return observation


def upsert_dwd_observations(conn, observations):
    if not observations:
        return 0
    sql = """
        INSERT INTO dwd.observations (
            station_id, ts_utc, resolution, source,
            temperature, humidity, cloudiness, wind_speed, wind_gust,
            wind_direction, pressure, rain, rain_rate_10min, sunshine
        ) VALUES (
            %(station_id)s, %(ts_utc)s, %(resolution)s, %(source)s,
            %(temperature)s, %(humidity)s, %(cloudiness)s, %(wind_speed)s, %(wind_gust)s,
            %(wind_direction)s, %(pressure)s, %(rain)s, %(rain_rate_10min)s, %(sunshine)s
        )
        ON CONFLICT (station_id, ts_utc, resolution, source) DO UPDATE SET
            temperature = COALESCE(EXCLUDED.temperature, dwd.observations.temperature),
            humidity = COALESCE(EXCLUDED.humidity, dwd.observations.humidity),
            cloudiness = COALESCE(EXCLUDED.cloudiness, dwd.observations.cloudiness),
            wind_speed = COALESCE(EXCLUDED.wind_speed, dwd.observations.wind_speed),
            wind_gust = COALESCE(EXCLUDED.wind_gust, dwd.observations.wind_gust),
            wind_direction = COALESCE(EXCLUDED.wind_direction, dwd.observations.wind_direction),
            pressure = COALESCE(EXCLUDED.pressure, dwd.observations.pressure),
            rain = COALESCE(EXCLUDED.rain, dwd.observations.rain),
            rain_rate_10min = COALESCE(EXCLUDED.rain_rate_10min, dwd.observations.rain_rate_10min),
            sunshine = COALESCE(EXCLUDED.sunshine, dwd.observations.sunshine),
            updated_at = now()
    """
    with conn.cursor() as cur:
        cur.executemany(sql, observations)
    conn.commit()
    return len(observations)


def scrape_high_res(args, session, conn, station_id, category, resolution, field_mapping):
    """Fetches 10-minute or hourly DWD data and upserts it into PostgreSQL."""
    if resolution == '10_minutes':
        prefix, ts_format = "10minutenwerte", "%Y%m%d%H%M"
        cat_map = {'air_temperature': 'TU', 'wind': 'wind', 'precipitation': 'nieder'}
        url_part = cat_map.get(category, category)
    else:
        prefix, ts_format = "stundenwerte", "%Y%m%d%H"
        cat_map = {'air_temperature': 'TU', 'wind': 'FF', 'precipitation': 'RR', 'pressure': 'P0', 'cloudiness': 'N'}
        url_part = cat_map.get(category, category)

    zip_filename = f"{prefix}_{url_part}_{station_id}_akt.zip"
    if not dwd_recent_index_contains_file(session, resolution, category, zip_filename):
        log_message("INFO", f"DWD dataset missing for station {station_id} (category={category}, resolution={resolution}); skipping fetch.")
        return 0

    url = f"https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/{resolution}/{category}/recent/{zip_filename}"
    log_message("INFO", f"Downloading DWD file {zip_filename}")
    z = fetch_dwd_zip(session, url)
    txt_filename = next((n for n in z.namelist() if n.startswith("produkt_") and n.endswith(".txt")), None)
    if not txt_filename:
        return 0
    with z.open(txt_filename) as f:
        content = f.read().decode('latin1')
    reader = csv.DictReader(io.StringIO(content), delimiter=';')
    observations = []
    count = 0
    for row in reader:
        row = {k.strip(): v.strip() for k, v in row.items() if k}
        dt_str = row.get('MESS_DATUM')
        if not dt_str:
            continue
        dt = datetime.strptime(dt_str, ts_format).replace(tzinfo=timezone.utc)
        metrics = build_dwd_metrics(row, field_mapping)
        if metrics:
            observations.append(build_dwd_observation(station_id, dt, resolution, category, metrics))
            count += 1
        if len(observations) >= 2000:
            upsert_dwd_observations(conn, observations)
            observations = []
    if observations:
        upsert_dwd_observations(conn, observations)
    log_message("INFO", f"Stored {count} DWD observations for category={category}, resolution={resolution}")
    return count


def check_history_loaded(conn, station_id):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT historical_kl_loaded FROM dwd.ingest_state WHERE station_id = %s",
            (station_id,),
        )
        row = cur.fetchone()
    return bool(row and row[0])


def mark_history_loaded(conn, station_id):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO dwd.ingest_state (
                station_id, historical_kl_loaded, historical_kl_loaded_at, updated_at
            ) VALUES (%s, true, now(), now())
            ON CONFLICT (station_id) DO UPDATE SET
                historical_kl_loaded = true,
                historical_kl_loaded_at = now(),
                updated_at = now()
            """,
            (station_id,),
        )
    conn.commit()


def get_last_daily_kl_run_date(conn, station_id):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT last_daily_kl_run_date FROM dwd.ingest_state WHERE station_id = %s",
            (station_id,),
        )
        row = cur.fetchone()
    return row[0] if row else None


def mark_daily_kl_run(conn, station_id, run_date):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO dwd.ingest_state (
                station_id, last_daily_kl_run_date, updated_at
            ) VALUES (%s, %s, now())
            ON CONFLICT (station_id) DO UPDATE SET
                last_daily_kl_run_date = EXCLUDED.last_daily_kl_run_date,
                updated_at = now()
            """,
            (station_id, run_date),
        )
    conn.commit()


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


def open_postgres_connection(args):
    return psycopg.connect(
        host=args.postgres_host,
        port=args.postgres_port,
        dbname=args.postgres_db,
        user=args.postgres_user,
        password=args.postgres_password,
        connect_timeout=10,
    )


def scrape_dwd_high_frequency(args, session, conn):
    station_id = args.dwd_station_id
    log_message("INFO", f"Fetching high-frequency DWD data for station {station_id}")

    jobs = [
        ('air_temperature', '10_minutes', {'TT_10': 'temperature', 'RF_10': 'humidity'}),
        ('wind', '10_minutes', {'FF_10': 'wind_speed', 'DD_10': 'wind_direction'}),
        ('precipitation', '10_minutes', {'RWS_10': 'rain_rate_10min'}),
        ('pressure', 'hourly', {'P0': 'pressure'}),
        ('cloudiness', 'hourly', {'N': 'cloudiness'}),
    ]
    total = 0
    for category, resolution, field_mapping in jobs:
        log_message("INFO", f"Starting DWD job category={category}, resolution={resolution}")
        count = run_with_db_retries(
            args,
            conn,
            f"DWD {category} Recent Error",
            lambda category=category, resolution=resolution, field_mapping=field_mapping: scrape_high_res(
                args, session, conn, station_id, category, resolution, field_mapping
            ),
            default=0,
        )
        log_message("INFO", f"Finished DWD job category={category}, resolution={resolution}, rows={count or 0}")
        total += count or 0
    log_message("INFO", f"Finished high-frequency DWD ingestion with total rows={total}")
    return total


def scrape_dwd_daily(args, session, conn):
    station_id = args.dwd_station_id

    if not run_with_db_retries(args, conn, "PostgreSQL DWD State Error", lambda: check_history_loaded(conn, station_id), default=True):
        log_message("INFO", f"Starting historical KL import for station {station_id}")
        hist_url = run_with_retries(args, "DWD Hist URL Error", lambda: get_dwd_historical_url(session, station_id))
        if hist_url:
            def load_hist():
                z = fetch_dwd_zip(session, hist_url)
                count = process_dwd_zip_kl(z, conn, station_id)
                mark_history_loaded(conn, station_id)
                log_message("INFO", f"Historical KL import complete for station {station_id}, rows={count}")
                return count
            run_with_db_retries(args, conn, "DWD Historical Data Error", load_hist)

    today = date.today()
    last_daily_run = run_with_db_retries(
        args,
        conn,
        "PostgreSQL DWD State Error",
        lambda: get_last_daily_kl_run_date(conn, station_id),
    )
    if last_daily_run == today:
        log_message("INFO", f"Daily KL already processed for station {station_id} today; skipping")
        return 0

    log_message("INFO", f"Fetching daily DWD KL data for station {station_id}")
    kl_url = f"https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/daily/kl/recent/tageswerte_KL_{station_id}_akt.zip"

    def load_daily_kl():
        count = process_dwd_zip_kl(fetch_dwd_zip(session, kl_url), conn, station_id)
        mark_daily_kl_run(conn, station_id, today)
        log_message("INFO", f"Daily KL import complete for station {station_id}, rows={count}")
        return count

    return run_with_db_retries(args, conn, "DWD KL Recent Error", load_daily_kl, default=0)


def scrape_dwd(args, session):
    if not args.dwd_station_id:
        return
    if not all([args.postgres_host, args.postgres_db, args.postgres_user, args.postgres_password]):
        raise ValueError("DWD PostgreSQL ingestion requires postgres host, database, user, and password.")

    with open_postgres_connection(args) as conn:
        if args.dwd_mode in ('all', 'high-frequency'):
            scrape_dwd_high_frequency(args, session, conn)
        if args.dwd_mode in ('all', 'daily'):
            scrape_dwd_daily(args, session, conn)

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
    p.add_argument("--dwd-mode", choices=("all", "high-frequency", "daily", "off"), default="off", help="DWD PostgreSQL ingestion mode")
    p.add_argument("--postgres-host", default="postgres")
    p.add_argument("--postgres-port", type=int, default=5432)
    p.add_argument("--postgres-db", default="timeseries")
    p.add_argument("--postgres-user")
    p.add_argument("--postgres-password")
    args = p.parse_args()

    log_message("INFO", f"Scrape run started (dwd_mode={args.dwd_mode}, dwd_station_id={args.dwd_station_id})")

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

    log_message("INFO", "Fetching Fam-Lange weather data")
    fam_data = run_with_retries(args, "Fam-Lange Weather Error",
                                lambda: parse_fam_lange(fetch_soup(sess_wx, "https://fam-lange.de/wetter.php")),
                                default={})
    log_message("INFO", f"Fam-Lange weather metrics fetched: {len(fam_data)}")

    log_message("INFO", "Fetching PegelOnline data")
    peg_data = run_with_retries(args, "PegelOnline Error",
                                lambda: parse_pegelonline(fetch_soup(sess_peg, "https://www.pegelonline.wsv.de/gast/stammdaten?pegelnr=501060")),
                                default={})
    log_message("INFO", f"PegelOnline metrics fetched: {len(peg_data)}")

    log_message("INFO", "Fetching solar data")
    solar_data = run_with_retries(args, "Solar Scrape Error",
                                  lambda: parse_solar(fetch_soup(sess_sol, "https://fam-lange.de/solar.php")),
                                  default={})
    log_message("INFO", f"Solar metrics fetched: {len(solar_data)}")

    if args.neon_ext_sensor_url:
        def scrape_neon_ext():
            resp = requests.get(args.neon_ext_sensor_url, timeout=10)
            resp.raise_for_status()
            sensor_val = parse_neon_ext_temp(resp.text)
            write_metric(write_api, args.influx_bucket, args.influx_org, "neonExtTempSensor", sensor_val)
        log_message("INFO", "Fetching and writing NEON external sensor data")
        run_with_retries(args, "Sensor Scrape Error", scrape_neon_ext)

    if args.neon_cpu_sensor_url:
        def scrape_neon_cpu():
            resp = requests.get(args.neon_cpu_sensor_url, timeout=10)
            resp.raise_for_status()
            sensor_val = parse_neon_cpu_temp(resp.text)
            write_metric(write_api, args.influx_bucket, args.influx_org, "neonCPUTempSensor", sensor_val)
        log_message("INFO", "Fetching and writing NEON CPU sensor data")
        run_with_retries(args, "Sensor Scrape Error", scrape_neon_cpu)

    if args.dwd_mode != "off":
        log_message("INFO", "Starting DWD PostgreSQL ingestion")
        run_with_retries(args, "DWD PostgreSQL Scrape Error", lambda: scrape_dwd(args, sess_wx))
        log_message("INFO", "Finished DWD PostgreSQL ingestion")

    merged_metrics = {**fam_data, **peg_data, **solar_data}
    for k, v in merged_metrics.items():
        if k == "totalenergy":
            continue
        run_with_retries(args, "InfluxDB Write Error",
                         lambda: write_metric(write_api, args.influx_bucket, args.influx_org, k, v),
                         body_prefix=f"{k}={v}: ")
    log_message("INFO", f"Finished writing {len([k for k in merged_metrics if k != 'totalenergy'])} metrics to InfluxDB")

    if "totalenergy" in solar_data:
        noon = datetime.combine(date.today(), dt_time(12, 0, 0), tzinfo=timezone.utc)
        run_with_retries(args, "InfluxDB Write Error",
                         lambda: write_metric(write_api, args.influx_bucket, args.influx_org, "totalenergy", solar_data["totalenergy"], timestamp=noon),
                         body_prefix=f"totalenergy={solar_data['totalenergy']}: ")
        log_message("INFO", "Wrote totalenergy metric to InfluxDB")

    write_api.close()
    client.close()
    log_message("INFO", "Scrape run completed")

if __name__ == "__main__":
    main()
