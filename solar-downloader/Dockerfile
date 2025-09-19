# Use a recent Alpine
FROM alpine:3.19

# install required packages:
# - bash : run your bash script
# - curl : fetch HTML + file (we'll use curl for robust downloads)
# - wget : included in case script uses it (kept for compatibility)
# - grep/sed/coreutils : text processing
# - dcron : cron daemon (lightweight)
# - tzdata : optional timezone support
# - ca-certificates : TLS for HTTPS
RUN apk add --no-cache \
    bash \
    curl \
    wget \
    grep \
    sed \
    coreutils \
    cronie \
    tzdata \
    ca-certificates

# create installation dir
RUN mkdir -p /usr/local/bin /opt/solar

# copy scripts
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
COPY solar-fetch.sh /usr/local/bin/solar-fetch.sh

# make executable
RUN chmod +x /usr/local/bin/entrypoint.sh /usr/local/bin/solar-fetch.sh

# set sane PATH and working dir
ENV PATH=/usr/local/bin:$PATH
WORKDIR /opt/solar

# default environment variables (can be overridden in docker-compose)
ENV URL="https://fam-lange.de/solar.php" \
    IMAGE_URL="https://fam-lange.de/pic/solar.png" \
    OUTPUT_DIR="/data" \
    PREFIX="" \
    CRON_SCHEDULE="30 23 * * *" \
    TZ="UTC" \
    RETRIES="2" \
    RETRY_DELAY="5"

# entrypoint runs cron in foreground
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD []

