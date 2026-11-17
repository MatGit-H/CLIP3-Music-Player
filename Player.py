from decoder.Decoder import Decoder
from shared.audio import CHANNELS, DTYPE, SAMPLE_RATE
from shared.song import SongStatus
import numpy as np
import queue
import sounddevice as sd
import threading


class Player:
    BLOCK = 1024
    BUFFER_SECONDS = 2.0
    TAP_FRAMES = 8192

    def __init__(self, on_song_end=None):
        self.on_song_end = on_song_end
        self.song = None
        self.volume = 1.0
        self.paused = False
        self._lock = threading.Lock()
        self._blocks = queue.Queue(maxsize=int(self.BUFFER_SECONDS * SAMPLE_RATE / self.BLOCK))
        self._generation = 0
        self._offset = 0.0
        self._frames_played = 0
        self._silence = np.zeros((self.BLOCK, CHANNELS), DTYPE)
        self._tap = np.zeros((self.TAP_FRAMES, CHANNELS), DTYPE)
        self._tap_pos = 0
        self._tap_lock = threading.Lock()
        self._stream = None
        self._latency_frames = 0

    def play(self, song, start=0.0):
        if not song.local_path:
            raise ValueError(f"{song.title!r} has no local file")
        self._ensure_stream()
        with self._lock:
            prev = self.song
            if prev is not None and prev is not song and prev.status == SongStatus.PLAYING:
                prev.status = SongStatus.DONE
            self.song = song
            song.status = SongStatus.PLAYING
            self.paused = False
            self._restart(start)

    def seek(self, seconds):
        with self._lock:
            if self.song is not None:
                self._restart(max(0.0, seconds))

    def seek_by(self, delta):
        self.seek(self.position + delta)

    def stop(self):
        with self._lock:
            self._generation += 1
            self._drain()
            if self.song is not None and self.song.status == SongStatus.PLAYING:
                self.song.status = SongStatus.DONE
            self.song = None

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def toggle_pause(self):
        self.paused = not self.paused

    def set_volume(self, volume):
        self.volume = min(1.0, max(0.0, volume))

    def close(self):
        self.stop()
        if self._stream is not None:
            self._stream.close()
            self._stream = None

    @property
    def position(self):
        if self.song is None:
            return 0.0
        return self._offset + max(0, self._frames_played - self._latency_frames) / SAMPLE_RATE

    def latest(self, frames):
        frames = min(frames, self.TAP_FRAMES)
        with self._tap_lock:
            end = self._tap_pos - self._latency_frames
            idx = np.arange(end - frames, end) % self.TAP_FRAMES
            return self._tap[idx].copy()

    def _ensure_stream(self):
        if self._stream is None:
            self._stream = sd.OutputStream(
                samplerate=SAMPLE_RATE, channels=CHANNELS, dtype='float32',
                blocksize=self.BLOCK, callback=self._callback,
            )
            self._stream.start()
            self._latency_frames = int(self._stream.latency * SAMPLE_RATE)

    def _restart(self, start):
        self._generation += 1
        self._offset = start
        self._frames_played = 0
        self._drain()
        threading.Thread(
            target=self._feed, args=(self.song, start, self._generation), daemon=True,
        ).start()

    def _drain(self):
        while True:
            try:
                self._blocks.get_nowait()
            except queue.Empty:
                return

    def _put(self, gen, item):
        while gen == self._generation:
            try:
                self._blocks.put((gen, item), timeout=0.1)
                return True
            except queue.Full:
                pass
        return False

    def _feed(self, song, start, gen):
        error = None
        try:
            with Decoder(song.local_path, start) as pcm:
                while gen == self._generation:
                    block = pcm.read(self.BLOCK)
                    if len(block) == 0:
                        break
                    if not self._put(gen, block):
                        return
        except Exception as e:
            error = str(e)
        done = threading.Event()
        if not self._put(gen, done):
            return
        while not done.wait(0.1):
            if gen != self._generation:
                return
        with self._lock:
            if gen != self._generation:
                return
            self.song = None
            if error:
                song.status = SongStatus.ERROR
                song.error = error
            elif song.status == SongStatus.PLAYING:
                song.status = SongStatus.DONE
        if self.on_song_end:
            self.on_song_end(song)

    def _next_block(self):
        while True:
            try:
                gen, item = self._blocks.get_nowait()
            except queue.Empty:
                return None
            if gen != self._generation:
                continue
            if isinstance(item, threading.Event):
                item.set()
                return None
            return item

    def _callback(self, outdata, frames, time_info, status):
        block = None if self.paused else self._next_block()
        if block is None:
            outdata.fill(0)
            self._push_tap(self._silence[:frames])
            return
        n = len(block)
        np.multiply(block, self.volume, out=outdata[:n])
        outdata[n:] = 0
        self._frames_played += n
        self._push_tap(block)

    def _push_tap(self, samples):
        n = len(samples)
        with self._tap_lock:
            pos = self._tap_pos
            first = min(n, self.TAP_FRAMES - pos)
            self._tap[pos:pos + first] = samples[:first]
            self._tap[:n - first] = samples[first:]
            self._tap_pos = (pos + n) % self.TAP_FRAMES
