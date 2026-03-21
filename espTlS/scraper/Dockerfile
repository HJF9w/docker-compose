FROM python:3.11-alpine
RUN pip install --no-cache-dir requests influxdb-client
WORKDIR /app
COPY scraper.py .
CMD ["python", "scraper.py"]
