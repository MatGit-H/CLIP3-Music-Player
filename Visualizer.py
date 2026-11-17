from shared.audio import SAMPLE_RATE
import numpy as np

BLOCKS = " ▁▂▃▄▅▆▇█"
# Braille cell: 4 rows x 2 cols — each bit OR'd into one character
_BITMASK = np.array([[0x01, 0x08], [0x02, 0x10], [0x04, 0x20], [0x40, 0x80]])


def to_mono(samples):
    return samples.mean(axis=1) if samples.ndim == 2 else samples


def _db_to_unit(amplitude, floor_db):
    db = 20 * np.log10(np.maximum(amplitude, 1e-10))
    return np.clip((db - floor_db) / -floor_db, 0.0, 1.0)


class Spectrum:
    def __init__(self, n_bars, fft_size=4096, fmin=40.0, fmax=16000.0,
                 floor_db=-70.0, tilt_db_per_octave=3.0, attack=0.6, decay=0.12):
        self.n_bars = n_bars
        self.fft_size = fft_size
        self.floor_db = floor_db
        self.attack = attack
        self.decay = decay
        self._window = np.hanning(fft_size)
        self._norm = self._window.sum() / 2

        freqs = np.fft.rfftfreq(fft_size, 1 / SAMPLE_RATE)
        starts = np.searchsorted(freqs, np.geomspace(fmin, fmax, n_bars + 1))
        # Low bands can share one FFT bin — force each bar its own bin
        for i in range(1, len(starts)):
            starts[i] = max(starts[i], starts[i - 1] + 1)
        starts = np.minimum(starts, len(freqs))
        self._bands = list(zip(starts[:-1], np.maximum(starts[1:], starts[:-1] + 1)))

        centers = np.array([freqs[min(lo, len(freqs) - 1)] for lo, _ in self._bands])
        self._tilt = 10 ** (tilt_db_per_octave * np.log2(np.maximum(centers, 1) / 1000) / 20)
        self.levels = np.zeros(n_bars)

    def update(self, samples):
        x = to_mono(samples)[-self.fft_size:]
        if len(x) < self.fft_size:
            x = np.pad(x, (self.fft_size - len(x), 0))
        mag = np.abs(np.fft.rfft(x * self._window)) / self._norm
        bands = np.array([mag[lo:hi].max() if lo < len(mag) else 0.0 for lo, hi in self._bands])
        target = _db_to_unit(bands * self._tilt, self.floor_db)
        rate = np.where(target > self.levels, self.attack, self.decay)
        self.levels += (target - self.levels) * rate
        return self.levels


def render_bars(levels, height):
    eighths = np.round(np.asarray(levels) * height * 8).astype(int)
    rows = []
    for row in range(height - 1, -1, -1):
        fill = np.clip(eighths - row * 8, 0, 8)
        rows.append("".join(BLOCKS[f] for f in fill))
    return rows


def waveform(samples, width, height, gain=1.0):
    x = to_mono(samples)
    if len(x) == 0:
        x = np.zeros(1)
    w, h = width * 2, height * 4

    starts = np.linspace(0, len(x), w, endpoint=False).astype(int)
    following = x[np.append(starts[1:], len(x) - 1)]
    lo = np.minimum(np.minimum.reduceat(x, starts), following)
    hi = np.maximum(np.maximum.reduceat(x, starts), following)

    def to_row(v):
        return np.round((1 - np.clip(v * gain, -1.0, 1.0)) / 2 * (h - 1)).astype(int)

    rows = np.arange(h)[:, None]
    grid = (rows >= to_row(hi)) & (rows <= to_row(lo))
    codes = (grid.reshape(height, 4, width, 2) * _BITMASK[None, :, None, :]).sum(axis=(1, 3))
    return ["".join(chr(0x2800 + c) for c in row) for row in codes]


def run_visualizers(visualizers, samples, width):
    rows = []
    for viz in visualizers:
        rows.extend(viz(samples, width))
    return rows
