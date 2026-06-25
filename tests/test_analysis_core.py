"""Pure analysis-core tests: key, notes, lyrics parse, mapping (no librosa/network)."""

import numpy as np

from songstem.analysis.keys import estimate_key, scale_notes
from songstem.analysis.lyrics import parse_lrc
from songstem.analysis.mapping import map_notes_to_lyrics
from songstem.analysis.models import LyricLine, NoteEvent
from songstem.analysis.notes import frames_to_events, hz_to_note, most_common_pitch_classes


# --- keys ---------------------------------------------------------------

def _profile(weights, tonic):
    return np.roll(np.array(weights), tonic)


_MAJOR = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
_MINOR = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]


def test_estimate_key_c_major():
    key = estimate_key(_profile(_MAJOR, 0))  # C major
    assert key.tonic == "C" and key.mode == "major"


def test_estimate_key_a_minor():
    key = estimate_key(_profile(_MINOR, 9))  # A minor
    assert key.tonic == "A" and key.mode == "minor"


def test_scale_notes_g_major():
    key = estimate_key(_profile(_MAJOR, 7))  # G major
    assert scale_notes(key) == ["G", "A", "B", "C", "D", "E", "F#"]


# --- notes --------------------------------------------------------------

def test_hz_to_note():
    assert hz_to_note(440.0) == ("A", 4)
    assert hz_to_note(0) is None


def test_frames_to_events_groups_runs():
    # Two A4 frames, a gap (unvoiced), then one C4 frame.
    times = [0.0, 0.1, 0.2, 0.3]
    freqs = [440.0, 440.0, 0.0, 261.63]
    voiced = [True, True, False, True]
    events = frames_to_events(times, freqs, voiced)
    assert [(e.pitch_class, e.octave) for e in events] == [("A", 4), ("C", 4)]
    assert events[0].onset == 0.0


def test_most_common_pitch_classes():
    events = [NoteEvent(0, 1, "A", 4), NoteEvent(1, 1, "A", 4), NoteEvent(2, 1, "C", 4)]
    assert most_common_pitch_classes(events, limit=2) == ["A", "C"]


# --- lyrics + mapping ---------------------------------------------------

def test_parse_lrc():
    lines = parse_lrc("[00:01.50]hello\n[00:03.00]world\n[bad]ignored-no-stamp-format\n")
    assert [(round(ln.time, 2), ln.text) for ln in lines] == [(1.5, "hello"), (3.0, "world")]


def test_map_notes_to_lyrics():
    events = [NoteEvent(0.2, 0.5, "A", 4), NoteEvent(1.2, 0.5, "C", 4), NoteEvent(1.4, 0.5, "C", 4)]
    lines = [LyricLine(0.0, "first"), LyricLine(1.0, "second")]
    mapped = map_notes_to_lyrics(events, lines)
    assert [(ln.text, note) for ln, note in mapped] == [("first", "A"), ("second", "C")]


# --- SyncedLyricsProvider (network lib mocked via sys.modules) -----------

def test_synced_lyrics_provider_parses(monkeypatch):
    import sys

    from songstem.analysis.lyrics import SyncedLyricsProvider

    fake = type("m", (), {"search": staticmethod(lambda q, **k: "[00:01.00]hi\n[00:02.00]bye")})
    monkeypatch.setitem(sys.modules, "syncedlyrics", fake)
    lines = SyncedLyricsProvider().fetch("Artist", "Title")
    assert [ln.text for ln in lines] == ["hi", "bye"]


def test_synced_lyrics_provider_degrades_to_none(monkeypatch):
    import sys

    from songstem.analysis.lyrics import SyncedLyricsProvider

    def boom(q, **k):
        raise RuntimeError("offline")

    monkeypatch.setitem(sys.modules, "syncedlyrics", type("m", (), {"search": staticmethod(boom)}))
    assert SyncedLyricsProvider().fetch("A", "T") is None
