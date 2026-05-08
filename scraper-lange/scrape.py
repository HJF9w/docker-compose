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

DWD_OBSERVATION_FLOAT_COLUMNS = {
    'temperature': 'DOUBLE PRECISION',
    'temperature_max': 'DOUBLE PRECISION',
    'temperature_min': 'DOUBLE PRECISION',
    'temperature_5cm': 'DOUBLE PRECISION',
    'temperature_ground_min': 'DOUBLE PRECISION',
    'temperature_wet_bulb': 'DOUBLE PRECISION',
    'temperature_dew_point': 'DOUBLE PRECISION',
    'humidity': 'DOUBLE PRECISION',
    'cloudiness': 'DOUBLE PRECISION',
    'wind_speed': 'DOUBLE PRECISION',
    'wind_gust': 'DOUBLE PRECISION',
    'wind_direction': 'DOUBLE PRECISION',
    'pressure': 'DOUBLE PRECISION',
    'pressure_station': 'DOUBLE PRECISION',
    'rain': 'DOUBLE PRECISION',
    'rain_rate_10min': 'DOUBLE PRECISION',
    'precipitation_duration_10min': 'DOUBLE PRECISION',
    'rain_indicator': 'DOUBLE PRECISION',
    'precipitation_form': 'DOUBLE PRECISION',
    'sunshine': 'DOUBLE PRECISION',
    'snow_depth': 'DOUBLE PRECISION',
    'vapor_pressure': 'DOUBLE PRECISION',
    'absolute_humidity': 'DOUBLE PRECISION',
    'quality_level': 'DOUBLE PRECISION',
    'quality_level_3': 'DOUBLE PRECISION',
    'quality_level_4': 'DOUBLE PRECISION',
    'quality_level_8': 'DOUBLE PRECISION',
}

DWD_OBSERVATION_COLUMNS = list(DWD_OBSERVATION_FLOAT_COLUMNS.keys())

DWD_DAILY_KL_FIELD_MAPPING = {
    'QN_3': 'quality_level_3',
    'QN_4': 'quality_level_4',
    'TMK': 'temperature',
    'TXK': 'temperature_max',
    'TNK': 'temperature_min',
    'TGK': 'temperature_ground_min',
    'UPM': 'humidity',
    'NM': 'cloudiness',
    'FM': 'wind_speed',
    'FX': 'wind_gust',
    'PM': 'pressure',
    'RSK': 'rain',
    'RSKF': 'precipitation_form',
    'SDK': 'sunshine',
    'SHK_TAG': 'snow_depth',
    'VPM': 'vapor_pressure',
}


def postgres_schema_exists(conn, schema_name):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = %s)",
            (schema_name,),
        )
        row = cur.fetchone()
    return bool(row and row[0])


def postgres_table_exists(conn, schema_name, table_name):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = %s
                  AND table_name = %s
            )
            """,
            (schema_name, table_name),
        )
        row = cur.fetchone()
    return bool(row and row[0])


def postgres_table_columns(conn, schema_name, table_name):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = %s
              AND table_name = %s
            """,
            (schema_name, table_name),
        )
        return {row[0] for row in cur.fetchall()}


def ensure_dwd_schema(conn):
    """Create DWD tables when absent and avoid owner-only DDL on existing tables."""
    if not postgres_schema_exists(conn, 'dwd'):
        with conn.cursor() as cur:
            cur.execute("CREATE SCHEMA dwd")
        conn.commit()

    created_observations = False
    if not postgres_table_exists(conn, 'dwd', 'observations'):
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE dwd.observations (
                    station_id TEXT NOT NULL,
                    ts_utc TIMESTAMPTZ NOT NULL,
                    resolution TEXT NOT NULL,
                    source TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    PRIMARY KEY (station_id, ts_utc, resolution, source)
                )
                """
            )
        conn.commit()
        created_observations = True

    observation_columns = postgres_table_columns(conn, 'dwd', 'observations')
    missing_observation_columns = [
        (column_name, column_type)
        for column_name, column_type in DWD_OBSERVATION_FLOAT_COLUMNS.items()
        if column_name not in observation_columns
    ]
    if missing_observation_columns:
        if created_observations:
            with conn.cursor() as cur:
                for column_name, column_type in missing_observation_columns:
                    cur.execute(f"ALTER TABLE dwd.observations ADD COLUMN {column_name} {column_type}")
            conn.commit()
        else:
            missing_names = ", ".join(column_name for column_name, _ in missing_observation_columns)
            log_message(
                "WARN",
                "dwd.observations is missing optional columns, but this user is not assumed "
                f"to own the table; skipping ALTER TABLE. Missing columns: {missing_names}",
            )

    created_ingest_state = False
    if not postgres_table_exists(conn, 'dwd', 'ingest_state'):
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE dwd.ingest_state (
                    station_id TEXT PRIMARY KEY,
                    historical_kl_loaded BOOLEAN NOT NULL DEFAULT false,
                    historical_kl_full_fields_loaded BOOLEAN NOT NULL DEFAULT false,
                    historical_kl_loaded_at TIMESTAMPTZ,
                    historical_kl_full_fields_loaded_at TIMESTAMPTZ,
                    last_daily_kl_run_date DATE,
                    last_daily_kl_full_fields_run_date DATE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
        conn.commit()
        created_ingest_state = True

    ingest_state_columns = postgres_table_columns(conn, 'dwd', 'ingest_state')
    ingest_state_column_definitions = {
        'historical_kl_loaded': 'BOOLEAN NOT NULL DEFAULT false',
        'historical_kl_full_fields_loaded': 'BOOLEAN NOT NULL DEFAULT false',
        'historical_kl_loaded_at': 'TIMESTAMPTZ',
        'historical_kl_full_fields_loaded_at': 'TIMESTAMPTZ',
        'last_daily_kl_run_date': 'DATE',
        'last_daily_kl_full_fields_run_date': 'DATE',
        'created_at': 'TIMESTAMPTZ NOT NULL DEFAULT now()',
        'updated_at': 'TIMESTAMPTZ NOT NULL DEFAULT now()',
    }
    missing_ingest_state_columns = [
        (column_name, column_type)
        for column_name, column_type in ingest_state_column_definitions.items()
        if column_name not in ingest_state_columns
    ]
    if missing_ingest_state_columns:
        if created_ingest_state:
            with conn.cursor() as cur:
                for column_name, column_type in missing_ingest_state_columns:
                    cur.execute(f"ALTER TABLE dwd.ingest_state ADD COLUMN {column_name} {column_type}")
            conn.commit()
        else:
            missing_names = ", ".join(column_name for column_name, _ in missing_ingest_state_columns)
            log_message(
                "WARN",
                "dwd.ingest_state is missing optional columns, but this user is not assumed "
                f"to own the table; skipping ALTER TABLE. Missing columns: {missing_names}",
            )


def fetch_dwd_zip(session, url):
    # Bumped timeout to 60s for historical files
    resp = session.get(url, timeout=60)
    resp.raise_for_status()
    return zipfile.ZipFile(io.BytesIO(resp.content))


def dwd_index_contains_file(session, resolution, category, file_set, filename):
    index_url = (
        "https://opendata.dwd.de/climate_environment/CDC/observations_germany/"
        f"climate/{resolution}/{category}/{file_set}/"
    )
    resp = session.get(index_url, timeout=30)
    resp.raise_for_status()
    exists = filename in resp.text
    log_message("INFO", f"DWD index check {resolution}/{category}/{file_set}: {'found' if exists else 'missing'} {filename}")
    return exists


def dwd_recent_index_contains_file(session, resolution, category, filename):
    return dwd_index_contains_file(session, resolution, category, 'recent', filename)

def process_dwd_zip_kl(z, conn, station_id):
    """Processes daily climate (KL) data and upserts it into PostgreSQL."""
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
        dt = datetime.strptime(dt_str, "%Y%m%d").replace(tzinfo=timezone.utc)
        metrics = build_dwd_metrics(row, DWD_DAILY_KL_FIELD_MAPPING)
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
    }
    observation.update({column: None for column in DWD_OBSERVATION_COLUMNS})
    observation.update(metrics)
    return observation


def upsert_dwd_observations(conn, observations):
    if not observations:
        return 0
    metric_columns_sql = ", ".join(DWD_OBSERVATION_COLUMNS)
    metric_placeholders_sql = ", ".join(f"%({column})s" for column in DWD_OBSERVATION_COLUMNS)
    update_sql = ",\n            ".join(
        f"{column} = COALESCE(EXCLUDED.{column}, dwd.observations.{column})"
        for column in DWD_OBSERVATION_COLUMNS
    )
    sql = f"""
        INSERT INTO dwd.observations (
            station_id, ts_utc, resolution, source,
            {metric_columns_sql}
        ) VALUES (
            %(station_id)s, %(ts_utc)s, %(resolution)s, %(source)s,
            {metric_placeholders_sql}
        )
        ON CONFLICT (station_id, ts_utc, resolution, source) DO UPDATE SET
            {update_sql},
            updated_at = now()
    """
    with conn.cursor() as cur:
        cur.executemany(sql, observations)
    conn.commit()
    return len(observations)


def dwd_high_res_file_parts(station_id, category, resolution, file_set):
    if resolution == '10_minutes':
        prefix, ts_format = "10minutenwerte", "%Y%m%d%H%M"
        cat_map = {'air_temperature': 'TU', 'wind': 'wind', 'precipitation': 'nieder'}
        url_part = cat_map.get(category, category)
    else:
        prefix, ts_format = "stundenwerte", "%Y%m%d%H"
        cat_map = {
            'air_temperature': 'TU',
            'wind': 'FF',
            'precipitation': 'RR',
            'pressure': 'P0',
            'cloudiness': 'N',
            'moisture': 'TF',
        }
        url_part = cat_map.get(category, category)

    suffix = 'now' if file_set == 'now' else 'akt'
    return f"{prefix}_{url_part}_{station_id}_{suffix}.zip", ts_format


def scrape_high_res_file(args, session, conn, station_id, category, resolution, field_mapping, file_set):
    zip_filename, ts_format = dwd_high_res_file_parts(station_id, category, resolution, file_set)
    if not dwd_index_contains_file(session, resolution, category, file_set, zip_filename):
        log_message(
            "INFO",
            f"DWD {file_set} dataset missing for station {station_id} "
            f"(category={category}, resolution={resolution}); skipping fetch.",
        )
        return 0

    url = (
        "https://opendata.dwd.de/climate_environment/CDC/observations_germany/"
        f"climate/{resolution}/{category}/{file_set}/{zip_filename}"
    )
    log_message("INFO", f"Downloading DWD {file_set} file {zip_filename}")
    z = fetch_dwd_zip(session, url)
    txt_filename = next((n for n in z.namelist() if n.startswith("produkt_") and n.endswith(".txt")), None)
    if not txt_filename:
        return 0
    with z.open(txt_filename) as f:
        content = f.read().decode('latin1')
    reader = csv.DictReader(io.StringIO(content), delimiter=';')
    observations = []
    count = 0
    first_dt = None
    last_dt = None
    for row in reader:
        row = {k.strip(): v.strip() for k, v in row.items() if k}
        dt_str = row.get('MESS_DATUM')
        if not dt_str:
            continue
        dt = datetime.strptime(dt_str, ts_format).replace(tzinfo=timezone.utc)
        first_dt = first_dt or dt
        last_dt = dt
        metrics = build_dwd_metrics(row, field_mapping)
        if metrics:
            observations.append(build_dwd_observation(station_id, dt, resolution, category, metrics))
            count += 1
        if len(observations) >= 2000:
            upsert_dwd_observations(conn, observations)
            observations = []
    if observations:
        upsert_dwd_observations(conn, observations)
    if first_dt and last_dt:
        log_message(
            "INFO",
            f"Stored {count} DWD {file_set} observations for category={category}, "
            f"resolution={resolution}, range={first_dt.isoformat()}..{last_dt.isoformat()}",
        )
    else:
        log_message("INFO", f"Stored {count} DWD {file_set} observations for category={category}, resolution={resolution}")
    return count


def scrape_high_res(args, session, conn, station_id, category, resolution, field_mapping):
    """Fetches 10-minute or hourly DWD data and upserts it into PostgreSQL."""
    total = scrape_high_res_file(args, session, conn, station_id, category, resolution, field_mapping, 'recent')
    if resolution == '10_minutes':
        total += scrape_high_res_file(args, session, conn, station_id, category, resolution, field_mapping, 'now')
    return total


def daily_kl_has_full_fields(conn, station_id):
    table_columns = postgres_table_columns(conn, 'dwd', 'observations')
    full_field_columns = [
        column
        for column in ('temperature_max', 'temperature_min', 'temperature_ground_min')
        if column in table_columns
    ]
    if not full_field_columns:
        return False

    full_field_condition = " OR ".join(f"{column} IS NOT NULL" for column in full_field_columns)
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT EXISTS (
                SELECT 1
                FROM dwd.observations
                WHERE station_id = %s
                  AND resolution = 'daily'
                  AND source = 'kl'
                  AND ({full_field_condition})
            )
            """,
            (station_id,),
        )
        row = cur.fetchone()
    return bool(row and row[0])


def check_history_loaded(conn, station_id):
    table_columns = postgres_table_columns(conn, 'dwd', 'ingest_state')
    state_column = None
    if 'historical_kl_full_fields_loaded' in table_columns:
        state_column = 'historical_kl_full_fields_loaded'
    elif 'historical_kl_loaded' in table_columns:
        state_column = 'historical_kl_loaded'

    if not state_column:
        return False

    with conn.cursor() as cur:
        cur.execute(
            f"SELECT {state_column} FROM dwd.ingest_state WHERE station_id = %s",
            (station_id,),
        )
        row = cur.fetchone()
    if not bool(row and row[0]):
        return False
    if daily_kl_has_full_fields(conn, station_id):
        return True
    log_message(
        "INFO",
        f"Historical KL state is set for station {station_id}, "
        "but no daily min/max/ground-min values were found; reimporting historical KL data.",
    )
    return False


def upsert_ingest_state(conn, station_id, values, params=None):
    params = list(params or [])
    table_columns = postgres_table_columns(conn, 'dwd', 'ingest_state')
    insert_columns = ['station_id']
    insert_values_sql = ['%s']
    query_params = [station_id]
    value_params = list(params)
    update_assignments = []

    for column, value_sql in values.items():
        if column in table_columns:
            insert_columns.append(column)
            insert_values_sql.append(value_sql)
            update_assignments.append(f"{column} = EXCLUDED.{column}")
            query_params.extend(value_params[:value_sql.count('%s')])
            del value_params[:value_sql.count('%s')]

    if 'updated_at' in table_columns:
        insert_columns.append('updated_at')
        insert_values_sql.append('now()')
        update_assignments.append('updated_at = now()')

    if update_assignments:
        conflict_sql = "DO UPDATE SET\n                " + ",\n                ".join(update_assignments)
    else:
        conflict_sql = "DO NOTHING"

    columns_sql = ", ".join(insert_columns)
    values_sql = ", ".join(insert_values_sql)
    with conn.cursor() as cur:
        cur.execute(
            f"""
            INSERT INTO dwd.ingest_state ({columns_sql})
            VALUES ({values_sql})
            ON CONFLICT (station_id) {conflict_sql}
            """,
            query_params,
        )
    conn.commit()


def mark_history_loaded(conn, station_id):
    upsert_ingest_state(
        conn,
        station_id,
        {
            'historical_kl_loaded': 'true',
            'historical_kl_loaded_at': 'now()',
            'historical_kl_full_fields_loaded': 'true',
            'historical_kl_full_fields_loaded_at': 'now()',
        },
    )


def get_last_daily_kl_run_date(conn, station_id):
    table_columns = postgres_table_columns(conn, 'dwd', 'ingest_state')
    if 'last_daily_kl_full_fields_run_date' in table_columns:
        state_column = 'last_daily_kl_full_fields_run_date'
    elif 'last_daily_kl_run_date' in table_columns:
        state_column = 'last_daily_kl_run_date'
    else:
        return None

    with conn.cursor() as cur:
        cur.execute(
            f"SELECT {state_column} FROM dwd.ingest_state WHERE station_id = %s",
            (station_id,),
        )
        row = cur.fetchone()
    return row[0] if row else None


def mark_daily_kl_run(conn, station_id, run_date):
    upsert_ingest_state(
        conn,
        station_id,
        {
            'last_daily_kl_run_date': '%s',
            'last_daily_kl_full_fields_run_date': '%s',
        },
        [run_date, run_date],
    )


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
        ('air_temperature', '10_minutes', {
            'QN': 'quality_level',
            'PP_10': 'pressure',
            'TT_10': 'temperature',
            'TM5_10': 'temperature_5cm',
            'RF_10': 'humidity',
            'TD_10': 'temperature_dew_point',
        }),
        ('wind', '10_minutes', {'QN': 'quality_level', 'FF_10': 'wind_speed', 'DD_10': 'wind_direction'}),
        ('precipitation', '10_minutes', {
            'QN': 'quality_level',
            'RWS_DAU_10': 'precipitation_duration_10min',
            'RWS_10': 'rain_rate_10min',
            'RWS_IND_10': 'rain_indicator',
        }),
        ('pressure', 'hourly', {'QN_8': 'quality_level_8', 'P0': 'pressure'}),
        ('cloudiness', 'hourly', {'QN_8': 'quality_level_8', 'N': 'cloudiness'}),
        ('precipitation', 'hourly', {
            'QN_8': 'quality_level_8',
            'R1': 'rain',
            'RS_IND': 'rain_indicator',
            'WRTR': 'precipitation_form',
        }),
        ('moisture', 'hourly', {
            'QN_8': 'quality_level_8',
            'ABSF_STD': 'absolute_humidity',
            'VP_STD': 'vapor_pressure',
            'TF_STD': 'temperature_wet_bulb',
            'P_STD': 'pressure_station',
            'TT_STD': 'temperature',
            'RF_STD': 'humidity',
            'TD_STD': 'temperature_dew_point',
        }),
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
        if daily_kl_has_full_fields(conn, station_id):
            log_message("INFO", f"Daily KL already processed for station {station_id} today; skipping")
            return 0
        log_message(
            "INFO",
            f"Daily KL state says station {station_id} was processed today, "
            "but no daily min/max/ground-min values were found; reprocessing daily KL data.",
        )

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
        ensure_dwd_schema(conn)
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
