"""Backend-agnostic data types for audio analysis and the cheat sheet.

Imports nothing heavy (no librosa/Qt/network), so these can be built and tested in isolation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# The twelve pitch classes, sharps spelling, indexed 0..11 starting at C.
PITCH_CLASSES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


@dataclass
class KeyEstimate:
    tonic: str  # e.g. "C#"
    mode: str  # "major" or "minor"
    confidence: float  # correlation score in roughly [-1, 1]

    @property
    def name(self) -> str:
        return f"{self.tonic} {self.mode}"


@dataclass
class NoteEvent:
    onset: float  # seconds
    duration: float  # seconds
    pitch_class: str  # e.g. "A#"
    octave: int

    @property
    def name(self) -> str:
        return f"{self.pitch_class}{self.octave}"


@dataclass
class LyricLine:
    time: float  # seconds from the start of the track
    text: str


@dataclass
class AudioAnalysis:
    key: KeyEstimate
    tempo_bpm: float
    duration: float  # seconds
    scale_notes: list[str] = field(default_factory=list)
    note_events: list[NoteEvent] = field(default_factory=list)
    # False for polyphonic stems (guitar/piano/other) where per-note detection is unreliable.
    notes_reliable: bool = True


@dataclass
class CheatSheet:
    title: str
    artist: str
    stem: str  # e.g. "bass"
    analysis: AudioAnalysis
    # Per-lyric-line dominant note (pitch class), or None. None overall = no lyrics available.
    lyric_notes: list[tuple[LyricLine, str | None]] | None = None
