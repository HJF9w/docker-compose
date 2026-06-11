# Use Python 3.12 on Alpine as requested
FROM python:3.15.0b2-alpine

# Metadata
LABEL maintainer="you@example.com" \
      description="Weather notifier container (Alpine, cron-driven)."

# Install runtime packages: tzdata for zoneinfo, bash for scripts, ca-certificates
# (crond is provided by busybox which is part of the image)
RUN apk add --no-cache tzdata bash ca-certificates \
 && update-ca-certificates

# Create app directories
WORKDIR /opt/weather_notifier

# Copy application files
COPY weather_notifier.py /usr/local/bin/weather_notifier.py
COPY run_weather.sh /usr/local/bin/run_weather.sh
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
COPY requirements.txt /opt/weather_notifier/requirements.txt

# Install python deps
RUN python -m pip install --upgrade pip \
 && pip install --no-cache-dir -r /opt/weather_notifier/requirements.txt

# Make scripts executable
RUN chmod +x /usr/local/bin/weather_notifier.py \
    /usr/local/bin/run_weather.sh \
    /usr/local/bin/entrypoint.sh

# Create logs directory (to be mounted from host ./logs)
RUN mkdir -p /logs \
 && chown root:root /logs

# Expose nothing; this container runs cron jobs and exits / runs in foreground
VOLUME ["/logs"]

# Default environment values (can be overridden by docker-compose)
ENV CRON_EXPR="0 6 * * *" \
    TZ="UTC" \
    LOG_FILES="/logs/dates.log" \
    IGNORE_DAYS="" \
    LATITUDE="0.0" \
    LONGITUDE="0.0" \
    SMTP_HOST="" \
    SMTP_PORT="587" \
    EMAIL_FROM="" \
    EMAIL_TO="" \
    TIMEZONE="" \
    EVENT_TIME="" \
    EVENT_TZ="" \
    SMTP_USER="" \
    SMTP_PASS=""

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

