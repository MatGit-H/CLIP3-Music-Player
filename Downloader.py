from yt_dlp import YoutubeDL
from spotdl import Spotdl
from spotdl.utils.config import DEFAULT_CONFIG
from pathlib import Path
from shared.song import Song, SongStatus
import threading


class Downloader:
    def __init__(self, url):
        self.url = url
        self.ydl_opts = {
            'format' : 'bestaudio',
            'extract_flat' : "in_playlist",
            'no_warnings' : True,
            'quiet' : True
        }
        self.download_opts = {
            'format' : 'bestaudio/best',
            'no_playlist' : True,
            'quiet' : True,
            'no_warnings' : True,
        }
        self.songs = {}
        self._thread = None
        self._stop = threading.Event()

    def _is_spotify(self, url):
        return "open.spotify.com" in url or url.startswith("spotify:")

    def extract_songs(self): 
        self.songs = {}
        if self._is_spotify(self.url):
            self._extract_spotify()
        else:
            self._extract_youtube()

    def _extract_youtube(self):
        with YoutubeDL(self.ydl_opts) as ydl:
            info = ydl.extract_info(self.url, download=False)

        entries = info.get('entries') if info.get('_type') == 'playlist' else [info]
        i = 0
        for entry in entries:
            if entry is None:
                continue
            song = Song.from_ydl_entry(entry)
            song.status = SongStatus.QUEUED
            self.songs[i] = (song.title, song.channel, f"{song.duration // 60}:{song.duration % 60:02d}")
            i += 1

    def _extract_spotify(self):
        spotdl = Spotdl(
            client_id=DEFAULT_CONFIG["client_id"],
            client_secret=DEFAULT_CONFIG["client_secret"],
        )
        results = spotdl.search([self.url])
        i = 0
        for entry in results:
            song = Song(
                id=entry.song_id,
                title=entry.name,
                page_url=entry.url,
                channel=entry.artist,
                duration=entry.duration,
                source="spotify",
                status=SongStatus.RESOLVING,
            )
            yt_url = spotdl.get_download_urls([entry])[0]
            song.stream_url = yt_url
            song.status = SongStatus.QUEUED
            self.songs[i] = (song.title, song.channel, f"{song.duration // 60}:{song.duration % 60:02d}")
            i += 1

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        Path("downloads").mkdir(parents=True, exist_ok=True)
        self.extract_songs()
        self._stop.clear()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join()

    def _worker(self):
        i = 0
        while not self._stop.is_set() and i < len(self.songs):
            self._download_one(self.songs[i])
            i += 1

    def _download_one(self, song):
        url = song.stream_url or song.page_url
        if not url:
            song.status = SongStatus.ERROR
            song.error = "missing url"
            return
        song.status = SongStatus.DOWNLOADING
        opts = {
            **self.download_opts,
            'outtmpl' : f"downloads/{song.title}.%(ext)s",
        }
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            song.local_path = ydl.prepare_filename(info)
        song.status = SongStatus.READY
