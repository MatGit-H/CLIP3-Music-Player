from shared.audio import CHANNELS, DTYPE, FRAME_BYTES, SAMPLE_RATE
import ffmpeg
import numpy as np
import subprocess


def probe_duration(path):
    result = subprocess.run(
        [
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'csv=p=0', path,
        ],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        return None


class Decoder:
    def __init__(self, path, start=0.0):
        self.path = path
        self.start = max(0.0, start)
        self._closed = False
        input_stream = ffmpeg.input(path, ss=self.start)
        output_stream = ffmpeg.output(
            input_stream.audio, 'pipe:',
            format='f32le', acodec='pcm_f32le',
            ar=SAMPLE_RATE, ac=CHANNELS,
        )
        self._proc = output_stream.run_async(
            pipe_stdout=True, pipe_stderr=True, quiet=True
        )

    def read(self, frames):
        data = self._proc.stdout.read(frames * FRAME_BYTES)
        n = len(data) // FRAME_BYTES
        if n == 0:
            self._check_exit()
        return np.frombuffer(data, dtype=DTYPE, count=n * CHANNELS).reshape(n, CHANNELS)

    def _check_exit(self):
        if self._proc.wait() != 0 and not self._closed:
            err = self._proc.stderr.read().decode(errors='replace').strip()
            raise RuntimeError(f"ffmpeg decode failed: {err[-300:]}")

    def close(self):
        self._closed = True
        if self._proc.poll() is None:
            self._proc.kill()
        self._proc.wait()
        self._proc.stdout.close()
        self._proc.stderr.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
