from Downloader import Downloader
downloader = Downloader("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
downloader.extract_songs()
for song_id, (title, channel, duration) in downloader.songs.items():
    print(f"Song ID: {song_id}, Title: {title}, Channel: {channel}, Duration: {duration}")