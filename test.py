from Downloader import Downloader

downloader = Downloader("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
downloader.start()
# start() runs download on a daemon thread — wait so the process doesn't exit early
if downloader._thread:
    downloader._thread.join()

for i, (title, channel, duration) in downloader.songs.items():
    print(
        f"[{i}] {title} | {channel} | {duration}"
    )
