#!/usr/bin/env python3
"""
🌦️ Monthly Weather Notifier Script 🌦️

Checks Open-Meteo forecast and sends an email notification when a suitable weather day
is found based on defined criteria. Logs each run in dates.log.
Supports a --debug flag for detailed output. Configuration can be overridden via CLI.
Includes option to attach an .ics calendar event at the chosen date/time, with a default reminder.

This variant supports multiple --log-file arguments; when multiple are given the script will
execute the full check/send/log sequence separately for each log file.
"""
import os
import sys
import csv
import smtplib
import argparse
import json
from datetime import datetime, date, timedelta, timezone
from email.message import EmailMessage
import requests

# Terminal colors
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
except Exception:
    class Fore:
        GREEN = ''
        YELLOW = ''
        RED = ''
        CYAN = ''
        MAGENTA = ''
    class Style:
        BRIGHT = ''
        RESET_ALL = ''

# Argument parsing
class CustomFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawTextHelpFormatter):
    pass

def parse_args():
    parser = argparse.ArgumentParser(
        description=(f"💡 {Style.BRIGHT}Monthly Weather Notifier{Style.RESET_ALL}\n"
                     "Fetch forecast, evaluate conditions, send email alerts, and optionally attach a calendar event."),
        formatter_class=CustomFormatter)

    parser.add_argument("--debug", action="store_true",
                        help="🔍 Enable verbose debug output")
    parser.add_argument("--latitude", type=float, help="📍 WGS84 latitude")
    parser.add_argument("--longitude", type=float, help="📍 WGS84 longitude")
    parser.add_argument("--smtp-host", help="📧 SMTP server host")
    parser.add_argument("--smtp-port", type=int, default=587,
                        help="📧 SMTP server port")
    parser.add_argument("--email-from", help="📧 From email address")
    parser.add_argument("--email-to", help="📧 To email address")
    parser.add_argument("--timezone", help="🌐 Timezone for forecast (e.g. 'Europe/Brussels').")
    # allow multiple log-file flags
    parser.add_argument("--log-file", action="append", default=None,
                        help="📝 Log file path (can be passed multiple times). Default: /logs/dates.log")
    parser.add_argument("--ignore-days", action="append", default=[],
                        help=("🚫 Dates or ranges to ignore (YYYY-MM-DD or YYYY-MM-DD..YYYY-MM-DD).\n"
                              "Example: --ignore-days 2025-05-01 --ignore-days 2025-05-04..2025-05-10"))
    parser.add_argument("--event-time", help="⏰ Time for calendar event (HH:MM)")
    parser.add_argument("--event-tz", help="🗺️ Timezone for calendar event (e.g. 'Europe/Brussels')")
    return parser.parse_args()

args = parse_args()

# Debug printing
def debug_print(*msg):
    if args.debug:
        print(Fore.CYAN + "[DEBUG]", *msg, file=sys.stderr)

# Load configuration (CLI takes precedence over env vars where applicable)
LATITUDE = args.latitude if args.latitude is not None else float(os.getenv("LATITUDE", "0.0"))
LONGITUDE = args.longitude if args.longitude is not None else float(os.getenv("LONGITUDE", "0.0"))
SMTP_HOST = args.smtp_host or os.getenv("SMTP_HOST", "")
SMTP_PORT = args.smtp_port or int(os.getenv("SMTP_PORT", "587"))
EMAIL_FROM = args.email_from or os.getenv("EMAIL_FROM", "")
EMAIL_TO = args.email_to or os.getenv("EMAIL_TO", "")
TIMEZONE = args.timezone or os.getenv("TIMEZONE", "")
# If CLI provided log files use them; otherwise take from env var LOG_FILES (comma-separated) or default
if args.log_file:
    LOG_FILES = args.log_file
else:
    env_logs = os.getenv("LOG_FILES", "")
    if env_logs:
        LOG_FILES = [p.strip() for p in env_logs.split(",") if p.strip()]
    else:
        LOG_FILES = ["/logs/dates.log"]

# Build ignore date ranges
ignore_ranges = []
# combine CLI ignore-days with env var IGNORE_DAYS (comma separated)
env_ignore = os.getenv("IGNORE_DAYS", "")
combined_ignores = list(args.ignore_days)
if env_ignore:
    combined_ignores += [i.strip() for i in env_ignore.split(",") if i.strip()]

for item in combined_ignores:
    parts = item.split('..')
    try:
        if len(parts) == 1:
            d = date.fromisoformat(parts[0]); ignore_ranges.append((d, d))
        else:
            start = date.fromisoformat(parts[0]); end = date.fromisoformat(parts[1])
            ignore_ranges.append((start, end))
    except ValueError:
        debug_print(Fore.YELLOW + f"Invalid ignore-days format: {item}")

# Timezone handling
try:
    from zoneinfo import ZoneInfo
    tz = ZoneInfo(TIMEZONE) if TIMEZONE else datetime.now().astimezone().tzinfo
except Exception:
    tz = timezone.utc

# Parameters (unchanged)
RAIN_THRESHOLD = 10
WARM_TEMP = 14.0
COLD_SUN_REQUIRED = 7.90 * 3600
SKIP_DAYS = 17
FORCE_DAYS = 20

# SMTP auth - use SMTP_USER / SMTP_PASS per your request
SMTP_USER = os.getenv("SMTP_USER") or os.getenv("emailUsername") or ""
SMTP_PASS = os.getenv("SMTP_PASS") or os.getenv("emailPassword") or ""

def ensure_log_exists(path):
    if not os.path.exists(os.path.dirname(path)):
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
        except Exception as e:
            debug_print("Could not create log directory:", e)
    if not os.path.exists(path):
        print(Fore.GREEN + "📝 Initializing log file:", path)
        try:
            with open(path, "w", newline="") as f:
                csv.writer(f, delimiter=";").writerow(
                    ["date","fgwd","fgwdDate","fgwdT","fgwdSH","sendEmailSuccess","message"] )
        except Exception as e:
            debug_print("Failed to init log file:", e)

def read_last_success(path):
    last_success = None
    entries_since = []
    try:
        with open(path, newline="") as f:
            for row in csv.DictReader(f, delimiter=";"):
                entries_since.append(row)
                if row.get("sendEmailSuccess") == "1":
                    try:
                        dt = datetime.fromisoformat(row["date"]).astimezone(tz)
                        last_success = max(last_success, dt) if last_success else dt
                    except Exception:
                        pass
    except FileNotFoundError:
        pass
    except Exception as e:
        debug_print("Error reading log file:", e)
    return last_success, entries_since

def fetch_forecast():
    print(Fore.CYAN + "🌐 Fetching forecast...")
    api_url = "https://api.open-meteo.com/v1/forecast"
    params = {"latitude":LATITUDE, "longitude":LONGITUDE,
              "daily":"temperature_2m_max,precipitation_probability_mean,sunshine_duration",
              "timezone":tz.key if hasattr(tz,'key') else 'UTC'}
    debug_print("Request params:", params)
    try:
        resp = requests.get(api_url, params=params, timeout=10); resp.raise_for_status()
        data = resp.json().get("daily", {})
        debug_print(json.dumps(data, indent=2))
        return data
    except Exception as e:
        print(Fore.RED + "❌ Weather API error:", e)
        return None

def evaluate_best(data, now, ignore_ranges, forcing):
    today_str = now.date().isoformat(); future=[]
    for d,t,r,s in zip(data.get("time",[]), data.get("temperature_2m_max",[]),
                      data.get("precipitation_probability_mean",[]), data.get("sunshine_duration",[])):
        if d<=today_str: continue
        d_obj = date.fromisoformat(d)
        if any(start<=d_obj<=end for start,end in ignore_ranges):
            print(Fore.YELLOW+f"🚫 Ignoring {d}"); continue
        future.append({"d":d,"t":t,"r":r,"s":s})
    print(Fore.MAGENTA + "🌅 Future days:")
    # window is chosen later by caller
    return future

def prepare_ics(best, event_time, event_tz, now, basename):
    try:
        from zoneinfo import ZoneInfo
        event_zone = ZoneInfo(event_tz)
        event_start = datetime.fromisoformat(best['d'] + "T" + event_time).replace(tzinfo=event_zone)
        event_end = event_start + timedelta(hours=1)
        dtstamp = now.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        dtstart = event_start.strftime('%Y%m%dT%H%M%S')
        dtend = event_end.strftime('%Y%m%dT%H%M%S')
        ics_lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//WeatherNotifier//EN",
            "BEGIN:VEVENT",
            f"UID:weather-{basename}-{best['d']}-{event_time}",
            f"DTSTAMP:{dtstamp}",
            f"DTSTART;TZID={event_tz}:{dtstart}",
            f"DTEND;TZID={event_tz}:{dtend}",
            f"SUMMARY:Good Weather Day {best['d']} ({basename})",
            "BEGIN:VALARM",
            "TRIGGER:PT0S",
            "ACTION:DISPLAY",
            "DESCRIPTION:Reminder: Good Weather Day event, FILTER säubern",
            "END:VALARM",
            "END:VEVENT",
            "END:VCALENDAR"
        ]
        ics_content = "\r\n".join(ics_lines).encode('utf-8')
        return ics_content
    except Exception as e:
        debug_print(Fore.RED + f"Error creating ICS: {e}")
        return None

def send_email(subject, body, attachment=None, attachment_filename="weather_event.ics"):
    msg=EmailMessage(); msg['Subject']=subject; msg['From']=EMAIL_FROM; msg['To']=EMAIL_TO
    msg.set_content(body)
    if attachment:
        # attachment is bytes
        msg.add_attachment(attachment, maintype='text', subtype='calendar', filename=attachment_filename)
    try:
        with smtplib.SMTP(SMTP_HOST,SMTP_PORT,timeout=10) as s:
            s.ehlo()
            s.starttls()
            if SMTP_USER:
                s.login(SMTP_USER,SMTP_PASS)
            s.send_message(msg)
        print(Fore.GREEN + "✅ Email sent!")
        return True, ""
    except Exception as e:
        print(Fore.RED + "❌ SMTP error:", e)
        return False, str(e)

def process_for_logfile(log_path):
    """
    Run the full workflow for a single log file path.
    Returns a tuple (exit_code, message)
    """
    # Determine basename for this log file (filename without extension)
    basename = os.path.splitext(os.path.basename(log_path))[0] if log_path else "log"

    # Ensure log exists
    ensure_log_exists(log_path)

    # Read previous entries
    last_success, entries_since = read_last_success(log_path)

    now = datetime.now(tz)
    print(Fore.MAGENTA + f"⏰ Current time: {now.isoformat()}")

    # Skip check
    if last_success and (now - last_success) < timedelta(days=SKIP_DAYS):
        print(Fore.YELLOW + "⚠️  Skip notification; last email sent at", last_success.isoformat())
        with open(log_path, "a", newline="") as f:
            csv.writer(f, delimiter=";").writerow([now.isoformat(),0,"","","",0,
                f"Skipped; last at {last_success.isoformat()}" ])
        return 0, "skipped_recent"

    # Determine window
    age_days = (now - last_success).days if last_success else FORCE_DAYS + 1
    forcing = age_days > FORCE_DAYS
    window = 5 if forcing else 3
    print(Fore.CYAN + ("🔥 Forcing mode" if forcing else "✔️ Normal mode"),
          f"→ Checking next {window} days")

    # Fetch forecast
    data = fetch_forecast()
    if not data:
        # If fetching failed, write a log entry and return non-zero
        with open(log_path, "a", newline="") as f:
            csv.writer(f, delimiter=";").writerow([now.isoformat(),0,"","","",0,
                "Weather API error"])
        return 2, "weather_api_error"

    future = evaluate_best(data, now, ignore_ranges, forcing)
    for item in future[:window]:
        print(f"  {item['d']}: {item['t']}°C, rain={item['r']}%, sun={item['s']}s")

    print(Fore.CYAN + "🔎 Evaluating candidates...")
    candidates=[i for i in future[:window] if i['r']<=RAIN_THRESHOLD and
                (forcing or i['t']>WARM_TEMP or i['s']>=COLD_SUN_REQUIRED)]
    if not candidates:
        print(Fore.YELLOW + "❗ No suitable weather found.")
        with open(log_path, "a", newline="") as f:
            csv.writer(f, delimiter=";").writerow([now.isoformat(),0,"","","",0,
                "No suitable weather"])
        return 0, "no_suitable_weather"

    # Select best candidate
    print(Fore.CYAN + "🎯 Selecting best candidate...")
    best=sorted(candidates, key=lambda x:(-x['s'],-x['t'],x['d']))[0]
    print(Fore.GREEN + f"✅ Selected: {best['d']} | {best['t']}°C | {best['s']/3600:.2f}h sun")

    # Prepare email (append basename to subject)
    subject=f"☀️ Weather Alert: {best['d']} | {best['t']}°C | {best['s']/3600:.2f}h ({basename})"
    body=("You're all set! Enjoy the sunshine. ☀️\n" if not forcing else
          "Forced notification. Check the logs for details. 🔥")

    # Add calendar event if requested (with default reminder)
    ics_content = None
    # event args may be CLI (-) or env var - use CLI first then env var
    event_time = args.event_time or os.getenv("EVENT_TIME", "")
    event_tz = args.event_tz or os.getenv("EVENT_TZ", "")
    if event_time and event_tz:
        ics_content = prepare_ics(best, event_time, event_tz, now, basename)
        if ics_content:
            debug_print(Fore.CYAN + "Added .ics calendar event with reminder for", best['d'], event_time)

    # Send email
    print(Fore.CYAN + "📧 Sending email...")
    attachment_filename = f"weather_event_{basename}.ics" if ics_content else None
    send_ok, err = send_email(subject, body, attachment=ics_content, attachment_filename=attachment_filename or "weather_event.ics")

    # Log result
    try:
        with open(log_path,'a',newline='') as f:
            csv.writer(f,delimiter=';').writerow([
                now.isoformat(),1,best['d'],best['t'],best['s'],1 if send_ok else 0, err])
        print(Fore.GREEN + "📝 Logged result.")
    except Exception as e:
        debug_print("Failed to write to log:", e)
        return 3, "log_write_error"

    return (0 if send_ok else 4), ("sent" if send_ok else err)

def main():
    overall_exit = 0
    results = []
    # Iterate over log files and perform the full flow per file
    for log_path in LOG_FILES:
        print(Fore.MAGENTA + f"\n=== Processing log: {log_path} ===")
        exit_code, message = process_for_logfile(log_path)
        results.append((log_path, exit_code, message))
        # track non-zero
        if exit_code != 0:
            overall_exit = exit_code if overall_exit == 0 else overall_exit

    # Summary
    print(Fore.MAGENTA + "\n=== Run summary ===")
    for path, code, msg in results:
        print(f"  {path}: exit={code} -> {msg}")

    sys.exit(overall_exit)

if __name__ == "__main__":
    main()

