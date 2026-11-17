from Downloader import Downloader

downloader = Downloader("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
downloader.start()
# start() runs download on a daemon thread — wait so the process doesn't exit early
if downloader._thread:
    downloader._thread.join()

for i, song in downloader.songs.items():
    duration = song.duration
    if duration is None:
        time_str = "?:??"
    else:
        s = int(duration)
        time_str = f"{s // 60}:{s % 60:02d}"
    print(f"[{i}] {song.title} | {song.channel} | {time_str} | {song.local_path} | {song.status}")
