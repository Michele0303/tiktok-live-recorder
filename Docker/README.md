# Docker Integration
## Presentation
This Docker image is for automatic downloading live of your favorite Tiktok creator.
Stream are downloaded in /download and it's mandatory to mount this directory to your host

## Builing
```bash
cd Docker
docker build -t tiktok-live-recorder:latest .
```
## Run a container 
Look the [Guide](../GUIDE.md#how-to-set-cookies)  about to set your COOKIE SESSION ID  and where yo find the Tiktok Username -> $TT_USER
```bash
docker run -it \
  -e TT_USER=tiktokusername \              # Mandatory
  -e SESSION_ID=YOUR_COOKIE_SESSION_ID \   # Optional, 
  -e TT_TARGET=eu-ttp2 \                   # Optional choose between [eu-ttp2,useast2a]
  -v /host/path/download:/download         # Path of your download
  --name tlr_container_name tiktok-live-recorder
  --restart unless-stopped
```
