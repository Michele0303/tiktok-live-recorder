FROM python:3.12-alpine
WORKDIR /download
WORKDIR /app
RUN apk add --no-cache ffmpeg gcc musl-dev
ADD ../src/ /app/tiktok-live-recorder
WORKDIR /app/tiktok-live-recorder/src
RUN pip install --no-cache-dir -r requirements.txt
ADD run.sh /app/tiktok-live-recorder/src
RUN ["/bin/chmod","+x","run.sh"]
CMD ["/bin/sh","-c","./run.sh"]