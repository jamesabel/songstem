"""Read and write audio files.

Output is always written with soundfile (libsndfile) — the app emits WAV/FLAC, which it
handles natively. Input is trickier: iTunes/Apple Music tracks are usually AAC/ALAC in an
`.m4a` container, which libsndfile cannot decode. `load` therefore tries soundfile first
and falls back to Demucs' ffmpeg-backed reader for compressed formats.

`.m4p` files are FairPlay DRM-protected (Apple Music subscription downloads / old protected
iTunes Store purchases). Their audio stream is encrypted (`drms`), so no decoder — ffmpeg
included — can read them, and they cannot be separated. We detect them up front and raise a
clear error rather than letting ffmpeg fail opaquely with exit status 69.

soundfile uses (frames, channels) ordering; AudioClip uses (channels, frames), so we
transpose at the boundary.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import numpy as np

from songstem.models import AudioClip

# Container extensions that hold FairPlay-encrypted audio.
_DRM_SUFFIXES = {".m4p"}


class DRMProtectedError(RuntimeError):
    """Raised when a file is DRM-protected and therefore cannot be decoded."""

    def __init__(self, path: Path) -> None:
        self.path = path
        super().__init__(
            f"{path.name} is DRM-protected (Apple FairPlay) and cannot be separated. "
            f"Use a DRM-free source: a CD rip, a DRM-free purchase, or an MP3."
        )


def is_drm_protected(path: Path) -> bool:
    """True if the path is a known DRM-protected container (e.g. iTunes `.m4p`)."""
    return path.suffix.lower() in _DRM_SUFFIXES


def load(path: Path) -> AudioClip:
    if is_drm_protected(path):
        raise DRMProtectedError(path)
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
        # ffmpeg returns exit status 69 on an encrypted (DRM) stream; surface that clearly.
        if "69" in str(exc):
            raise DRMProtectedError(path) from exc
        raise RuntimeError(
            f"Cannot decode {path.name}: {exc}. The file may be corrupt or in a format "
            f"ffmpeg cannot read."
        ) from exc

    return AudioClip(samples=wav.numpy().astype(np.float32), sample_rate=sample_rate)


def save(clip: AudioClip, path: Path) -> Path:
    import soundfile as sf

    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), np.ascontiguousarray(clip.samples.T), clip.sample_rate)
    return path


def save_atomic(clip: AudioClip, path: Path) -> Path:
    """Save `clip` so `path` only ever exists as a complete file.

    Writes to a temp file in the destination directory (same filesystem, so the rename is
    atomic) and `os.replace`s it into place. If writing is interrupted by a crash or shutdown,
    `path` is either absent or the previous complete version — never a half-written file. A
    leftover `.tmp` may remain after a crash; it is ignored by readers and cleaned on next run.
    """
    import soundfile as sf

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f"{path.stem}-", suffix=".tmp")
    os.close(fd)
    tmp = Path(tmp_name)
    # The temp keeps a `.tmp` suffix (so readers never mistake it for a finished file), so
    # soundfile can't infer the container from the name — pass it from the destination.
    fmt = path.suffix.lstrip(".").upper() or None
    try:
        sf.write(str(tmp), np.ascontiguousarray(clip.samples.T), clip.sample_rate, format=fmt)
        os.replace(tmp, path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    return path


def has_audio_content(path: Path, min_seconds: float, peak_threshold: float = 1e-4) -> bool:
    """True if `path` is a readable audio file at least `min_seconds` long and not silent.

    Cheap: the duration is read from the header (no sample decode) and short-circuits before
    scanning; the silence check reads blocks and stops at the first sample above the threshold.
    """
    import soundfile as sf

    try:
        info = sf.info(str(path))
    except Exception:
        return False
    if not info.samplerate or info.frames / info.samplerate < min_seconds:
        return False
    try:
        with sf.SoundFile(str(path)) as f:
            for block in f.blocks(blocksize=1 << 16, dtype="float32"):
                if block.size and float(np.abs(block).max()) >= peak_threshold:
                    return True
    except Exception:
        return False
    return False
