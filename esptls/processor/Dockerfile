FROM python:3.15-slim-bookworm@sha256:122756f3fe72c4f5d3d71897888204ee85774bc79de952555b8a474e1d0a5d53

# Install system dependencies
RUN apt-get update && apt-get install -y \
    enfuse \
    imagemagick \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
RUN pip install --no-cache-dir requests influxdb-client Pillow numpy

WORKDIR /app
COPY processor.py .

CMD ["python", "processor.py"]
