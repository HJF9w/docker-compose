FROM alpine:3.24
RUN apk add --no-cache ffmpeg python3
WORKDIR /app
COPY timelapse.py .
CMD ["python3", "timelapse.py"]
