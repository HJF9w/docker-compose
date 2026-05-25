# Use Alpine as base
FROM python:3.14.5-alpine

# Set environment variables
ENV TZ=UTC \
    PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1

# Install dependencies
RUN apk update
RUN apk add --no-cache \
        ffmpeg \
        tzdata \
        bash \
        curl \
        git \
        && cp /usr/share/zoneinfo/$TZ /etc/localtime \
        && echo $TZ > /etc/timezone

WORKDIR /root

# Install Streamlink
RUN pip install --upgrade pip \
    && pip install yt-dlp schedule

ENV PATH=/root/.local/bin:$PATH

# Copy the Python script
COPY twitch_recorder.py .

# Healthcheck: check if Python script is running
HEALTHCHECK --interval=60s --timeout=10s --retries=3 CMD pgrep -f twitch_recorder.py || exit 1

# Default command
CMD ["python", "twitch_recorder.py"]

