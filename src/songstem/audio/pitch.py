"""Pitch-shift re-recorded WAVs into new transposed files.

`shift_pitch` is the pure primitive (one AudioClip in, a transposed AudioClip out) and
`shift_songs` is the testable batch loop that writes a new WAV per song. Both keep the heavy
`librosa` import local (per the project convention) and expose injectable seams (`shift`,
`load`, `save`) so the loop can be exercised without librosa or real audio — mirroring
`recording.session.record_playlist`.

The transpose unit is whole semitones (half-steps): +2 = a whole step up, -1 = a half step
down. Zero is a no-op. Output filenames carry the shift, e.g. 'Artist - Title [+2st].wav'.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from songstem.audio import io
from songstem.models import AudioClip, Song
from songstem.utils.naming import pitch_shifted_filename

ProgressCallback = Callable[["PitchShiftResult"], None]


@dataclass
class PitchShiftResult:
    song: Song
    source: Path | None
    path: Path | None = None
    semitones: int = 0
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


def shift_pitch(clip: AudioClip, semitones: int) -> AudioClip:
    """Return `clip` transposed by `semitones` half-steps (0 = unchanged).

    Each channel row of `clip.samples` (shaped (channels, frames)) is shifted independently;
    the sample rate, channel count, and frame count are preserved.
    """
    if semitones == 0:
        return clip
    import librosa

    rows = [
        librosa.effects.pitch_shift(
            clip.samples[ch], sr=clip.sample_rate, n_steps=float(semitones)
        )
        for ch in range(clip.channels)
    ]
    samples = np.ascontiguousarray(np.stack(rows), dtype=np.float32)
    return AudioClip(samples=samples, sample_rate=clip.sample_rate)


def shift_songs(
    items: list[tuple[Song, Path, int]],
    *,
    on_result: ProgressCallback | None = None,
    should_stop: Callable[[], bool] = lambda: False,
    shift: Callable[[AudioClip, int], AudioClip] = shift_pitch,
    load: Callable[[Path], AudioClip] = io.load,
    save: Callable[[AudioClip, Path], Path] = io.save_atomic,
) -> list[PitchShiftResult]:
    """Write a transposed WAV for each `(song, source, semitones)` item.

    Per-item failures are captured in the returned list rather than aborting the batch.
    `should_stop` is polled between items so the caller can cancel promptly. Each output is
    written next to its source as `<source stem> [±Nst].wav` via an atomic write.
    """
    results: list[PitchShiftResult] = []
    for song, source, semitones in items:
        if should_stop():
            break
        try:
            clip = load(source)
            shifted = shift(clip, semitones)
            dest = source.with_name(pitch_shifted_filename(source, semitones))
            path = save(shifted, dest)
            result = PitchShiftResult(
                song=song, source=source, path=path, semitones=semitones
            )
        except Exception as exc:
            result = PitchShiftResult(
                song=song, source=source, semitones=semitones, error=str(exc)
            )
        results.append(result)
        if on_result is not None:
            on_result(result)
    return results
