FROM python:3.11-alpine
RUN apk add --no-cache imagemagick enblend-enfuse ttf-dejavu
RUN pip install --no-cache-dir requests influxdb-client Pillow numpy
WORKDIR /app
COPY processor.py .
CMD ["python", "processor.py"]
