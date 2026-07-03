FROM python:3.14.6-alpine
RUN pip install --no-cache-dir requests
WORKDIR /app
COPY telegram_sender.py .
CMD ["python", "telegram_sender.py"]
