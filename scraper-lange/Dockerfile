FROM python:3.14-alpine

# Install build dependencies required by some Python packages and tzdata
# We include rust/cargo because some packages (cryptography, wheels) may require it on musl builds.
# We install only at build time and remove build deps afterwards where possible.
RUN apk add --no-cache --update \
        build-base \
        libffi-dev \
        openssl-dev \
        musl-dev \
        cargo \
        rust \
        tzdata \
        bash \
    && rm -rf /var/cache/apk/*

# Create app user and directory
ENV APP_DIR=/app
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
RUN mkdir -p ${APP_DIR}
WORKDIR ${APP_DIR}
COPY requirements.txt ${APP_DIR}/requirements.txt

# Install Python dependencies
# using --no-cache-dir to keep image small
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# Copy application files
# (we assume you will put your existing scrape.py into the same build context)
COPY scrape.py ${APP_DIR}/scrape.py
COPY entrypoint.py /usr/local/bin/entrypoint.py
COPY healthcheck.py /usr/local/bin/healthcheck.py
RUN chmod +x /usr/local/bin/entrypoint.py /usr/local/bin/healthcheck.py

# Ensure app folder owned by non-root
RUN chown -R appuser:appgroup ${APP_DIR}

# Switch to non-root user for running the app
USER appuser

# Default environment variables (can be overridden)
ENV CRON_SCHEDULE="" \
    TZ="" \
    INTERVAL_SECONDS="" \
    INFLUX_URL="" \
    INFLUX_TOKEN="" \
    INFLUX_ORG="" \
    INFLUX_BUCKET="" \
    POSTGRES_HOST="" \
    POSTGRES_PORT="" \
    POSTGRES_DB="" \
    POSTGRES_USER="" \
    POSTGRES_PASSWORD="" \
    DWD_MODE="off" \
    SMTP_HOST="" \
    SMTP_PORT="" \
    SMTP_USE_TLS="false" \
    SMTP_USER="" \
    SMTP_PASS="" \
    EMAIL_FROM="" \
    EMAIL_TO=""

# Healthcheck: run the python healthcheck script. Keep intervals reasonable.
HEALTHCHECK --interval=1m --timeout=10s --start-period=30s --retries=3 \
  CMD python /usr/local/bin/healthcheck.py

# Entrypoint
ENTRYPOINT ["/usr/local/bin/entrypoint.py"]
# Default: run once and exit (CRON_SCHEDULE empty)
CMD []

