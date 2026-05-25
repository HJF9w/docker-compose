FROM python:3.14.5-alpine
RUN pip install --no-cache-dir requests influxdb-client
WORKDIR /app
COPY scraper.py .
CMD ["python", "scraper.py"]
