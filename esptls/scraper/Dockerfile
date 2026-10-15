FROM python:3.15.0-alpine@sha256:ff4d3c9b1a48f646eedd93182aaea385c7a5452f4c8a8cd7cef686babacf4928
RUN pip install --no-cache-dir requests influxdb-client
WORKDIR /app
COPY scraper.py .
CMD ["python", "scraper.py"]
