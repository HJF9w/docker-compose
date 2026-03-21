FROM python:3.11-slim-bookworm

# Install system dependencies
RUN apt-get update && apt-get install -y \
    enblend-enfuse \
    imagemagick \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
RUN pip install --no-cache-dir requests influxdb-client Pillow numpy

WORKDIR /app
COPY processor.py .

CMD ["python", "processor.py"]
