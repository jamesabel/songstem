"""Read and write audio files via soundfile (libsndfile).

soundfile uses (frames, channels) ordering; AudioClip uses (channels, frames), so both
functions transpose at the boundary.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from songstem.models import AudioClip


def load(path: Path) -> AudioClip:
    import soundfile as sf

    data, sample_rate = sf.read(str(path), dtype="float32", always_2d=True)
    return AudioClip(samples=data.T.copy(), sample_rate=sample_rate)


def save(clip: AudioClip, path: Path) -> Path:
    import soundfile as sf

    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), np.ascontiguousarray(clip.samples.T), clip.sample_rate)
    return path
