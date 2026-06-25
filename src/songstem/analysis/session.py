"""Orchestrate cheat-sheet generation for one isolated stem.

Mirrors the injectable-seam style of `recording/session.py`: the analyzer and lyrics provider
are passed in (real or fake), so the whole flow is testable without librosa or the network.
"""

from __future__ import annotations

from pathlib import Path

from songstem.analysis.analyzer import AudioAnalyzer
from songstem.analysis.cheatsheet import build_markdown
from songstem.analysis.lyrics import LyricsProvider
from songstem.analysis.mapping import map_notes_to_lyrics
from songstem.analysis.models import CheatSheet
from songstem.models import AudioClip, Song, StemType
from songstem.utils.naming import cheatsheet_filename

# Stems where per-note pitch tracking is reliable enough for the notes/lyric-notes sections.
_MONOPHONIC = {StemType.BASS, StemType.VOCALS}


def generate_cheat_sheet(
    clip: AudioClip,
    song: Song,
    target: StemType,
    output_dir: Path,
    analyzer: AudioAnalyzer,
    lyrics_provider: LyricsProvider | None = None,
    *,
    fetch_lyrics: bool = True,
) -> Path:
    """Analyze `clip` and write a cheat-sheet `.md` next to the stem. Returns its path."""
    monophonic = target in _MONOPHONIC
    analysis = analyzer.analyze(clip, monophonic)

    lyric_notes = None
    if fetch_lyrics and lyrics_provider is not None:
        lines = lyrics_provider.fetch(song.artist, song.title)
        if lines:
            if monophonic and analysis.note_events:
                lyric_notes = map_notes_to_lyrics(analysis.note_events, lines)
            else:
                lyric_notes = [(line, None) for line in lines]

    sheet = CheatSheet(
        title=song.title,
        artist=song.artist,
        stem=target.value,
        analysis=analysis,
        lyric_notes=lyric_notes,
    )
    path = output_dir / cheatsheet_filename(song, target.value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_markdown(sheet), encoding="utf-8")
    return path


class CheatSheetMaker:
    """Bundles the analyzer + lyrics provider so the pipeline can make sheets with one call."""

    def __init__(
        self,
        analyzer: AudioAnalyzer,
        lyrics_provider: LyricsProvider | None = None,
        *,
        fetch_lyrics: bool = True,
    ) -> None:
        self._analyzer = analyzer
        self._lyrics_provider = lyrics_provider
        self._fetch_lyrics = fetch_lyrics

    def make(self, clip: AudioClip, song: Song, target: StemType, output_dir: Path) -> Path:
        return generate_cheat_sheet(
            clip, song, target, output_dir,
            self._analyzer, self._lyrics_provider, fetch_lyrics=self._fetch_lyrics,
        )


def default_maker(fetch_lyrics: bool = True) -> CheatSheetMaker:
    """A maker backed by the real librosa analyzer and synced-lyrics provider."""
    from songstem.analysis.analyzer import LibrosaAnalyzer
    from songstem.analysis.lyrics import SyncedLyricsProvider

    return CheatSheetMaker(LibrosaAnalyzer(), SyncedLyricsProvider(), fetch_lyrics=fetch_lyrics)
