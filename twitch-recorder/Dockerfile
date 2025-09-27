# Use Alpine as base
FROM python:3.13-alpine

# Set environment variables
ARG USERNAME=appuser
ENV TZ=UTC \
    PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1

# Install dependencies
RUN apk add --no-cache \
        ffmpeg \
        tzdata \
        bash \
        curl \
        git \
        && cp /usr/share/zoneinfo/$TZ /etc/localtime \
        && echo $TZ > /etc/timezone

# Create non-root user
RUN adduser -D -h /home/$USERNAME $USERNAME
WORKDIR /home/$USERNAME
USER $USERNAME

# Install Streamlink
RUN pip install --upgrade pip \
    && pip install streamlink schedule

ENV PATH=/home/$USERNAME/.local/bin:$PATH

# Copy the Python script
COPY twitch_recorder.py .

# Healthcheck: check if Python script is running
HEALTHCHECK --interval=60s --timeout=10s --retries=3 CMD pgrep -f twitch_recorder.py || exit 1

# Default command
CMD ["python", "twitch_recorder.py"]

