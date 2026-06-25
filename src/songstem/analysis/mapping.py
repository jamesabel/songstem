"""Map note events to lyric lines by timestamp (approximate, not forced alignment)."""

from __future__ import annotations

from collections.abc import Sequence

from songstem.analysis.models import PITCH_CLASSES, LyricLine, NoteEvent


def map_notes_to_lyrics(
    events: Sequence[NoteEvent],
    lines: Sequence[LyricLine],
) -> list[tuple[LyricLine, str | None]]:
    """For each lyric line, the dominant (modal) pitch class sung during it, or None.

    Each line owns the interval from its timestamp to the next line's (the last line runs to
    the end). The dominant pitch class is the most frequent among events whose onset falls in
    the interval; ties break to the earliest onset.
    """
    ordered = sorted(lines, key=lambda ln: ln.time)
    result: list[tuple[LyricLine, str | None]] = []
    for i, line in enumerate(ordered):
        start = line.time
        end = ordered[i + 1].time if i + 1 < len(ordered) else float("inf")
        in_line = [e for e in events if start <= e.onset < end]
        result.append((line, _dominant_pitch_class(in_line)))
    return result


def _dominant_pitch_class(events: list[NoteEvent]) -> str | None:
    if not events:
        return None
    counts: dict[str, int] = {}
    first_onset: dict[str, float] = {}
    for e in events:
        counts[e.pitch_class] = counts.get(e.pitch_class, 0) + 1
        first_onset.setdefault(e.pitch_class, e.onset)
    return min(counts, key=lambda pc: (-counts[pc], first_onset[pc], PITCH_CLASSES.index(pc)))
