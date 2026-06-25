"""Extract key, tempo, and notes from an AudioClip.

`AudioAnalyzer` is the seam the session depends on; `LibrosaAnalyzer` is the real
implementation (librosa imported locally, so importing this module stays cheap), and
`FakeAnalyzer` returns canned results for tests.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from songstem.analysis import keys
from songstem.analysis.models import AudioAnalysis, KeyEstimate, NoteEvent
from songstem.analysis.notes import frames_to_events
from songstem.models import AudioClip

# Plausible f0 range for bass/vocals, used to bound pyin.
_FMIN_HZ = 55.0  # ~A1
_FMAX_HZ = 1000.0  # ~B5


class AudioAnalyzer(ABC):
    @abstractmethod
    def analyze(self, clip: AudioClip, monophonic: bool) -> AudioAnalysis:
        """Estimate key + tempo always; extract notes only when `monophonic` is True."""


class LibrosaAnalyzer(AudioAnalyzer):
    def analyze(self, clip: AudioClip, monophonic: bool) -> AudioAnalysis:
        import librosa

        y = np.asarray(clip.samples, dtype=np.float32)
        y = y.mean(axis=0) if y.ndim == 2 else y  # mono mix
        sr = clip.sample_rate

        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        key = keys.estimate_key(chroma.mean(axis=1))

        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        tempo_bpm = float(np.atleast_1d(tempo)[0])

        note_events: list[NoteEvent] = []
        if monophonic:
            note_events = self._extract_notes(librosa, y, sr)

        return AudioAnalysis(
            key=key,
            tempo_bpm=tempo_bpm,
            duration=clip.duration_seconds,
            scale_notes=keys.scale_notes(key),
            note_events=note_events,
            notes_reliable=monophonic,
        )

    @staticmethod
    def _extract_notes(librosa, y: np.ndarray, sr: int) -> list[NoteEvent]:
        f0, voiced, _ = librosa.pyin(y, fmin=_FMIN_HZ, fmax=_FMAX_HZ, sr=sr)
        times = librosa.times_like(f0, sr=sr)
        freqs = np.nan_to_num(f0, nan=0.0)
        return frames_to_events(times.tolist(), freqs.tolist(), voiced.tolist())


class FakeAnalyzer(AudioAnalyzer):
    """Returns a fixed AudioAnalysis (its `notes_reliable` follows the `monophonic` arg)."""

    def __init__(self, analysis: AudioAnalysis | None = None) -> None:
        self._analysis = analysis

    def analyze(self, clip: AudioClip, monophonic: bool) -> AudioAnalysis:
        if self._analysis is not None:
            return self._analysis
        return AudioAnalysis(
            key=KeyEstimate("C", "major", 1.0),
            tempo_bpm=120.0,
            duration=clip.duration_seconds,
            scale_notes=keys.scale_notes(KeyEstimate("C", "major", 1.0)),
            note_events=[NoteEvent(0.0, 0.5, "C", 3)] if monophonic else [],
            notes_reliable=monophonic,
        )
