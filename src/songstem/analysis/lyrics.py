"""Fetch time-stamped lyrics (best-effort) for note→lyric mapping.

`LyricsProvider` is the seam the cheat-sheet session depends on, so it can be tested with a
fake. `SyncedLyricsProvider` is the real network adapter (local `import syncedlyrics`). Lyrics
are copyrighted; this is a best-effort, personal-use convenience that degrades to None whenever
nothing synced is found or the network is unavailable.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod

from songstem.analysis.models import LyricLine

# Matches one or more [mm:ss.xx] stamps at the start of a line, then the text.
_LRC_STAMP = re.compile(r"\[(\d+):(\d{1,2}(?:\.\d+)?)\]")


def parse_lrc(text: str) -> list[LyricLine]:
    """Parse LRC text into time-ordered LyricLines (lines without a stamp or text dropped)."""
    lines: list[LyricLine] = []
    for raw in text.splitlines():
        stamps = list(_LRC_STAMP.finditer(raw))
        if not stamps:
            continue
        content = raw[stamps[-1].end():].strip()
        if not content:
            continue
        for m in stamps:
            seconds = int(m.group(1)) * 60 + float(m.group(2))
            lines.append(LyricLine(time=seconds, text=content))
    lines.sort(key=lambda ln: ln.time)
    return lines


class LyricsProvider(ABC):
    @abstractmethod
    def fetch(self, artist: str, title: str) -> list[LyricLine] | None:
        """Time-stamped lyrics for the track, or None if unavailable."""


class SyncedLyricsProvider(LyricsProvider):
    """Best-effort synced lyrics via the `syncedlyrics` package."""

    def fetch(self, artist: str, title: str) -> list[LyricLine] | None:
        if not title:
            return None
        try:
            import syncedlyrics

            lrc = syncedlyrics.search(f"{title} {artist}".strip(), synced_only=True)
        except Exception:
            return None  # offline, not found, or library/runtime error — degrade silently
        if not lrc:
            return None
        lines = parse_lrc(lrc)
        return lines or None


class FakeLyricsProvider(LyricsProvider):
    """In-memory provider for tests/dev."""

    def __init__(self, lines: list[LyricLine] | None = None) -> None:
        self._lines = lines

    def fetch(self, artist: str, title: str) -> list[LyricLine] | None:
        return list(self._lines) if self._lines else None
