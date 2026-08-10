FROM python:3.14.7-alpine

LABEL maintainer="you@example.com"
ENV PYTHONUNBUFFERED=1

# Install system packages: cronie for cron, tzdata if you want timezone support
RUN apk add --no-cache cronie tzdata

WORKDIR /usr/src/app

# Copy the script
COPY del_mail.py /usr/local/bin/del_mail.py
RUN chmod +x /usr/local/bin/del_mail.py

# Copy entrypoint
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Ensure logfile exists
RUN touch /var/log/cron.log && chmod 644 /var/log/cron.log

# No Python external deps required (imaplib is stdlib).
# If you add dependencies later, add requirements.txt and uncomment pip install lines:
# COPY requirements.txt /usr/src/app/requirements.txt
# RUN pip install --no-cache-dir -r /usr/src/app/requirements.txt

# Expose nothing; container runs cron in foreground
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD []

