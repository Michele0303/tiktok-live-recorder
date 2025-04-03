FROM python:3.12-alpine
WORKDIR /download
WORKDIR /app/tiktok-live-recorder
RUN apk add --no-cache ffmpeg gcc musl-dev
ADD src/ /app/tiktok-live-recorder/src
WORKDIR /app/tiktok-live-recorder/src
RUN pip install --no-cache-dir -r requirements.txt
ADD ./Docker/run.sh /app/tiktok-live-recorder/src
RUN ["/bin/chmod","+x","run.sh"]
CMD ["/bin/sh","-c","./run.sh"]