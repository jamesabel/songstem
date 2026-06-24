"""Read and write audio files.

Output is always written with soundfile (libsndfile) — the app emits WAV/FLAC, which it
handles natively. Input is trickier: iTunes/Apple Music tracks are usually AAC/ALAC in an
`.m4a` container, which libsndfile cannot decode. `load` therefore tries soundfile first
and falls back to Demucs' ffmpeg-backed reader for compressed formats.

soundfile uses (frames, channels) ordering; AudioClip uses (channels, frames), so we
transpose at the boundary.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from songstem.models import AudioClip


def load(path: Path) -> AudioClip:
    try:
        return _load_soundfile(path)
    except Exception:
        # Compressed/iTunes formats (.m4a AAC/ALAC, .mp3) land here.
        return _load_ffmpeg(path)


def _load_soundfile(path: Path) -> AudioClip:
    import soundfile as sf

    data, sample_rate = sf.read(str(path), dtype="float32", always_2d=True)
    return AudioClip(samples=data.T.copy(), sample_rate=sample_rate)


def _load_ffmpeg(path: Path) -> AudioClip:
    """Decode via Demucs' AudioFile, which shells out to ffmpeg.

    Requires the `ffmpeg` binary on PATH; raises a clear error if it is missing.
    """
    try:
        from demucs.audio import AudioFile
    except ImportError as exc:  # pragma: no cover - depends on optional ML stack
        raise RuntimeError(
            f"Cannot decode {path.name}: soundfile failed and Demucs is not installed."
        ) from exc

    try:
        audio_file = AudioFile(str(path))
        wav = audio_file.read(streams=0)  # (channels, frames) at the file's sample rate
        sample_rate = int(audio_file.samplerate())
    except Exception as exc:
        raise RuntimeError(
            f"Cannot decode {path.name}: {exc}. Decoding AAC/ALAC (.m4a) requires ffmpeg "
            f"on PATH."
        ) from exc

    return AudioClip(samples=wav.numpy().astype(np.float32), sample_rate=sample_rate)


def save(clip: AudioClip, path: Path) -> Path:
    import soundfile as sf

    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), np.ascontiguousarray(clip.samples.T), clip.sample_rate)
    return path
