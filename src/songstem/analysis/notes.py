"""Pure helpers to turn per-frame pitch tracks into discrete note events.

No librosa import — `analyzer.LibrosaAnalyzer` runs pyin and hands the frame arrays here.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from songstem.analysis.models import PITCH_CLASSES, NoteEvent


def hz_to_note(hz: float) -> tuple[str, int] | None:
    """Map a frequency to (pitch_class, octave), or None for non-positive input."""
    if hz is None or hz <= 0 or math.isnan(hz):
        return None
    midi = int(round(69 + 12 * math.log2(hz / 440.0)))
    return PITCH_CLASSES[midi % 12], midi // 12 - 1


def frames_to_events(
    times: Sequence[float],
    freqs: Sequence[float],
    voiced: Sequence[bool],
) -> list[NoteEvent]:
    """Group consecutive frames of the same note into NoteEvents.

    `times`, `freqs`, `voiced` are parallel per-frame arrays (frame time, f0 in Hz, voiced
    flag). Unvoiced frames break runs and are not emitted.
    """
    events: list[NoteEvent] = []
    cur: tuple[str, int] | None = None
    onset = 0.0
    last_time = 0.0

    def flush(end: float) -> None:
        if cur is not None:
            events.append(NoteEvent(onset, max(0.0, end - onset), cur[0], cur[1]))

    for i, t in enumerate(times):
        note = hz_to_note(freqs[i]) if (i < len(voiced) and voiced[i]) else None
        if note != cur:
            flush(t)
            cur = note
            onset = t
        last_time = t
    flush(last_time)
    return events


def most_common_pitch_classes(events: Sequence[NoteEvent], limit: int = 4) -> list[str]:
    """The most frequently played pitch classes, most-common first."""
    counts: dict[str, int] = {}
    for ev in events:
        counts[ev.pitch_class] = counts.get(ev.pitch_class, 0) + 1
    ordered = sorted(counts, key=lambda pc: (-counts[pc], PITCH_CLASSES.index(pc)))
    return ordered[:limit]
