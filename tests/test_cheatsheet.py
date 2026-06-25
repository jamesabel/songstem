"""Cheat-sheet Markdown builder + session orchestration (fakes; no librosa/network)."""

import numpy as np

from songstem.analysis.analyzer import FakeAnalyzer
from songstem.analysis.cheatsheet import PageBudget, build_markdown
from songstem.analysis.lyrics import FakeLyricsProvider
from songstem.analysis.models import (
    AudioAnalysis,
    CheatSheet,
    KeyEstimate,
    LyricLine,
    NoteEvent,
)
from songstem.analysis.session import generate_cheat_sheet
from songstem.models import AudioClip, Song, StemType


def _analysis(reliable=True):
    return AudioAnalysis(
        key=KeyEstimate("C#", "minor", 0.9),
        tempo_bpm=128.4,
        duration=231.0,
        scale_notes=["C#", "D#", "E", "F#", "G#", "A", "B"],
        note_events=[NoteEvent(0, 1, "C#", 2), NoteEvent(1, 1, "G#", 2)] if reliable else [],
        notes_reliable=reliable,
    )


def _clip(seconds=2.0, sr=8000):
    return AudioClip(np.zeros((2, int(seconds * sr)), dtype=np.float32), sr)


def test_markdown_has_header_key_tempo_scale():
    sheet = CheatSheet("Song", "Artist", "bass", _analysis(), None)
    md = build_markdown(sheet)
    assert "# Song — Artist" in md
    assert "C# minor" in md and "128 BPM" in md and "Bass" in md
    assert "3:51" in md  # 231s
    assert "**Scale:** C# D# E F# G# A B" in md


def test_markdown_monophonic_lyrics_notes_table():
    lyric_notes = [(LyricLine(0, "line one"), "C#"), (LyricLine(2, "line two"), "G#")]
    sheet = CheatSheet("S", "A", "vocals", _analysis(), lyric_notes)
    md = build_markdown(sheet)
    assert "### Lyrics & notes" in md and "| line one | C# |" in md


def test_markdown_polyphonic_is_reduced():
    sheet = CheatSheet("S", "A", "guitar", _analysis(reliable=False), None)
    md = build_markdown(sheet)
    assert "isn't reliable for polyphonic" in md
    assert "Most-used notes" not in md and "### Lyrics & notes" not in md


def test_markdown_respects_lyric_budget():
    lyric_notes = [(LyricLine(i, f"line {i}"), "C#") for i in range(100)]
    sheet = CheatSheet("S", "A", "bass", _analysis(), lyric_notes)
    md = build_markdown(sheet, PageBudget(max_lyric_lines=10))
    # Header (2) + separator (1) + at most 10 rows.
    assert md.count("\n| line") <= 10


def test_session_writes_md_with_lyric_notes(tmp_path):
    lines = [LyricLine(0.0, "hello"), LyricLine(1.5, "world")]
    path = generate_cheat_sheet(
        _clip(), Song(title="T", artist="A"), StemType.BASS, tmp_path,
        FakeAnalyzer(), FakeLyricsProvider(lines),
    )
    assert path.name == "A - T [bass cheatsheet].md"
    text = path.read_text(encoding="utf-8")
    assert "### Lyrics & notes" in text


def test_session_polyphonic_and_no_lyrics(tmp_path):
    path = generate_cheat_sheet(
        _clip(), Song(title="T", artist="A"), StemType.GUITAR, tmp_path,
        FakeAnalyzer(), FakeLyricsProvider(None),
    )
    text = path.read_text(encoding="utf-8")
    assert "isn't reliable for polyphonic" in text
    assert "### Lyrics" not in text  # no lyrics available → section omitted
