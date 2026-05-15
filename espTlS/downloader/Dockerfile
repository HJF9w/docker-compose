FROM python:3.14.5-alpine
RUN pip install --no-cache-dir requests
WORKDIR /app
COPY downloader.py .
CMD ["python", "downloader.py"]
