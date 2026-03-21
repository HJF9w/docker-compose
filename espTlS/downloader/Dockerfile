FROM python:3.11-alpine
RUN pip install --no-cache-dir requests
WORKDIR /app
COPY downloader.py .
CMD ["python", "downloader.py"]
