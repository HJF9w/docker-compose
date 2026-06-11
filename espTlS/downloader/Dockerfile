FROM python:3.15.0b2-alpine
RUN pip install --no-cache-dir requests
WORKDIR /app
COPY downloader.py .
CMD ["python", "downloader.py"]
