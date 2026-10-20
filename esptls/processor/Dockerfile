FROM python:3.15-slim-bookworm@sha256:2a41267d9de9d358f77a1de356e0f16ecba8d39827855be0ce9ef4792edce402

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
