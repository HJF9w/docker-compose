#!/usr/bin/env python3
import argparse
import re
import sys
import time
import smtplib
from email.message import EmailMessage
from datetime import datetime, date, time as dt_time, timezone

import requests
from bs4 import BeautifulSoup
from influxdb_client import InfluxDBClient, Point

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
    # locate the solar section by its id
    section = soup.find("section", id="content1-1y")
    if not section:
        raise ValueError("Solar section #content1-1y not found")
    # within that, find the <div class="mbr-text"> containing two <p> tags
    container = section.find("div", class_="mbr-text")
    if not container:
        raise ValueError("Solar container in section not found")
    ps = container.find_all("p")
    if len(ps) < 2:
        raise ValueError("Expected two <p> tags in solar data block")
    # second <p> has our data
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
    # expect exactly "extTempSensor=XX.XX" (allowing optional minus sign)
    m = re.match(r"^extTempSensor=(-?\d+\.?\d*)$", text.strip())
    if not m:
        raise ValueError(f"Unexpected sensor response: {text[:100]}")
    return m.group(1)

def parse_neon_cpu_temp(text):
    # expect exactly "cpuTemp=XX.X" (allowing optional minus sign)
    m = re.match(r"^cpuTemp=(-?\d+\.?\d*)$", text.strip())
    if not m:
        raise ValueError(f"Unexpected sensor response: {text[:100]}")
    return m.group(1)

def write_metric(write_api, bucket, org, key, value, timestamp=None):
    point = Point(key).field("value", float(value))
    if timestamp:
        point = point.time(timestamp)
    write_api.write(bucket=bucket, org=org, record=point)

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
    args = p.parse_args()

    client = InfluxDBClient(
        url=args.influx_url,
        token=args.influx_token,
        org=args.influx_org
    )
    write_api = client.write_api()

    sess_wx   = requests.Session()
    sess_peg  = requests.Session()
    sess_sol  = requests.Session()

    # weather
    fam_data = run_with_retries(args, "Fam-Lange Weather Error",
                                lambda: parse_fam_lange(fetch_soup(sess_wx, "https://fam-lange.de/wetter.php")),
                                default={})

    # water
    peg_data = run_with_retries(args, "PegelOnline Error",
                                lambda: parse_pegelonline(fetch_soup(sess_peg, "https://www.pegelonline.wsv.de/gast/stammdaten?pegelnr=501060")),
                                default={})

    # solar
    solar_data = run_with_retries(args, "Solar Scrape Error",
                                  lambda: parse_solar(fetch_soup(sess_sol, "https://fam-lange.de/solar.php")),
                                  default={})

    # neon external sensor
    if args.neon_ext_sensor_url:
        def scrape_neon_ext():
            resp = requests.get(args.neon_ext_sensor_url, timeout=10)
            resp.raise_for_status()
            sensor_val = parse_neon_ext_temp(resp.text)
            write_metric(write_api, args.influx_bucket, args.influx_org, "neonExtTempSensor", sensor_val)
        run_with_retries(args, "Sensor Scrape Error", scrape_neon_ext)

    # neon cpu sensor
    if args.neon_cpu_sensor_url:
        def scrape_neon_cpu():
            resp = requests.get(args.neon_cpu_sensor_url, timeout=10)
            resp.raise_for_status()
            sensor_val = parse_neon_cpu_temp(resp.text)
            write_metric(write_api, args.influx_bucket, args.influx_org, "neonCPUTempSensor", sensor_val)
        run_with_retries(args, "Sensor Scrape Error", scrape_neon_cpu)

    # write all but solar totalenergy
    for k, v in {**fam_data, **peg_data, **solar_data}.items():
        if k == "totalenergy":
            continue
        run_with_retries(args, "InfluxDB Write Error",
                         lambda: write_metric(write_api, args.influx_bucket, args.influx_org, k, v),
                         body_prefix=f"{k}={v}: ")

    # write solar totalenergy at 12:00 UTC
    if "totalenergy" in solar_data:
        noon = datetime.combine(date.today(), dt_time(12, 0, 0), tzinfo=timezone.utc)
        run_with_retries(args, "InfluxDB Write Error",
                         lambda: write_metric(write_api, args.influx_bucket, args.influx_org, "totalenergy", solar_data["totalenergy"], timestamp=noon),
                         body_prefix=f"totalenergy={solar_data['totalenergy']}: ")

    write_api.close()
    client.close()

if __name__ == "__main__":
    main()

