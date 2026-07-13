# Use Python 3.12 on Alpine as base
FROM python:3.14-alpine

# Metadata
LABEL maintainer="you@example.com" \
      description="Allsky camera Telegram notifier (Alpine, cron-driven with ffmpeg/scp)."

# Install runtime packages:
# - bash : run script wrapper/entrypoint
# - ffmpeg : process & convert video files
# - openssh-client : scp/ssh tool to download videos
# - tzdata : configure local timezone
# - ca-certificates : trust store for HTTPS calls to Telegram
RUN apk add --no-cache \
    bash \
    ffmpeg \
    openssh-client \
    tzdata \
    ca-certificates \
 && update-ca-certificates

# Create app directory
WORKDIR /opt/tl_conv

# Copy application files
COPY requirements.txt /opt/tl_conv/requirements.txt
COPY tl_conv.py /usr/local/bin/tl_conv.py
COPY entrypoint.sh /usr/local/bin/entrypoint.sh

# Install Python dependencies
RUN python -m pip install --upgrade pip \
 && pip install --no-cache-dir -r /opt/tl_conv/requirements.txt

# Make scripts executable
RUN chmod +x /usr/local/bin/tl_conv.py \
             /usr/local/bin/entrypoint.sh

# Create logs directory
RUN mkdir -p /logs \
 && chown root:root /logs

# Mount logs directory
VOLUME ["/logs"]

# Default environment values (can be overridden by docker-compose/env files)
ENV CRON_EXPR="37 51 7 * * *" \
    TZ="Europe/Berlin" \
    DELAY_DAYS="2" \
    DOWNLOAD_METHOD="scp" \
    SSH_USER="user" \
    SSH_PORT="22" \
    VIDEO_WIDTH="2592" \
    VIDEO_HEIGHT="1944"

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
