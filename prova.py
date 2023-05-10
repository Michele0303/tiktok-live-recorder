import requests
from urllib.parse import urljoin
from moviepy.editor import VideoFileClip, concatenate_videoclips

playlist_url = 'https://pull-hls-f16-gcp01.tiktokcdn.com/stage/stream-3283529153973059756_or4/index.m3u8'
response = requests.get(playlist_url)
playlist = response.text.strip().split('\n')

# Find the media segment lines in the playlist
media_segments = [line for line in playlist if not line.startswith('#')]

# Combine the media segment URLs with the playlist URL to create valid URLs
media_urls = [urljoin(playlist_url, segment_url) for segment_url in media_segments]

# Download each media segment and save it to a file
clips = []
for i, segment_url in enumerate(media_urls):
    response = requests.get(segment_url)
    with open(f'segment_{i}.ts', 'wb') as f:
        f.write(response.content)
    clip = VideoFileClip(f'segment_{i}.ts')
    clips.append(clip)

# Concatenate the clips and save the result as an .mp4 file
final_clip = concatenate_videoclips(clips)
final_clip.write_videofile('merged_video.mp4')
