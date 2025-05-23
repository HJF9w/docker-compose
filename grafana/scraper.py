#!/usr/bin/env python3
import argparse
import re
import sys
import smtplib
from email.message import EmailMessage
from datetime import datetime, date, time, timezone

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
    try:
        fam = fetch_soup(sess_wx, "https://fam-lange.de/wetter.php")
        fam_data = parse_fam_lange(fam)
    except Exception as e:
        send_error_email(args, "Fam‑Lange Weather Error", str(e))
        fam_data = {}

    # water
    try:
        peg = fetch_soup(sess_peg, "https://www.pegelonline.wsv.de/gast/stammdaten?pegelnr=501060")
        peg_data = parse_pegelonline(peg)
    except Exception as e:
        send_error_email(args, "PegelOnline Error", str(e))
        peg_data = {}

    # solar
    try:
        sol = fetch_soup(sess_sol, "https://fam-lange.de/solar.php")
        solar_data = parse_solar(sol)
    except Exception as e:
        send_error_email(args, "Solar Scrape Error", str(e))
        solar_data = {}

    # write all but solar totalenergy
    for k, v in {**fam_data, **peg_data, **solar_data}.items():
        if k == "totalenergy":
            continue
        try:
            write_metric(write_api, args.influx_bucket, args.influx_org, k, v)
        except Exception as e:
            send_error_email(args, "InfluxDB Write Error", f"{k}={v}: {e}")

    # write solar totalenergy at 12:00 UTC
    if "totalenergy" in solar_data:
        try:
            noon = datetime.combine(date.today(), time(12, 0, 0), tzinfo=timezone.utc)
            print (noon)
            print("Writing totalenergy:", solar_data["totalenergy"], "at", noon.isoformat())
            write_metric(write_api, args.influx_bucket, args.influx_org, "totalenergy", solar_data["totalenergy"], timestamp="12:00:00")
        except Exception as e:
            send_error_email(args, "InfluxDB Write Error", f"totalenergy={solar_data['totalenergy']}: {e}")

    write_api.close()
    client.close()

if __name__ == "__main__":
    main()

