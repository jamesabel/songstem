"""Core data types shared across the application.

These are intentionally backend-agnostic: nothing here imports PySide, Demucs, or the
iTunes COM layer, so the models can be used and tested in isolation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import numpy as np


class StemType(str, Enum):
    """An audio part that a separation backend can isolate.

    Values match Demucs' 6-source model labels so backends can map directly.
    """

    VOCALS = "vocals"
    BASS = "bass"
    DRUMS = "drums"
    GUITAR = "guitar"
    PIANO = "piano"
    OTHER = "other"


@dataclass
class AudioClip:
    """In-memory audio.

    samples: float32 array shaped (channels, frames), range roughly [-1.0, 1.0].
    """

    samples: np.ndarray
    sample_rate: int

    @property
    def channels(self) -> int:
        return self.samples.shape[0]

    @property
    def frames(self) -> int:
        return self.samples.shape[1]

    @property
    def duration_seconds(self) -> float:
        return self.frames / self.sample_rate if self.sample_rate else 0.0


@dataclass
class Song:
    """A track sourced from an Apple Music / iTunes playlist."""

    title: str
    artist: str
    album: str = ""
    # Local media path as reported by iTunes; may be None for cloud-only tracks.
    location: Path | None = None
    # iTunes persistent ID — stable across sessions, used for dedup/caching.
    persistent_id: str = ""


@dataclass
class SeparationJob:
    """One unit of batch work: produce solo + muted files for `target` of `song`."""

    song: Song
    target: StemType
    output_dir: Path
    # Per-stem gain multipliers applied when building the muted mix (1.0 = unchanged).
    # The `target` stem's gain is forced to 0.0 for the muted output.
    stem_gains: dict[StemType, float] = field(default_factory=dict)


@dataclass
class JobResult:
    """Outcome of a completed (or failed) SeparationJob."""

    job: SeparationJob
    solo_path: Path | None = None
    muted_path: Path | None = None
    cheatsheet_path: Path | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None
