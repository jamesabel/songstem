"""Guarded test of the real librosa-backed analyzer on a synthetic monophonic tone."""

import numpy as np
import pytest

from songstem.models import AudioClip, StemType

pytest.importorskip("librosa")

from songstem.analysis.analyzer import LibrosaAnalyzer  # noqa: E402


def _tone(hz, seconds=3.0, sr=22050):
    t = np.arange(int(seconds * sr)) / sr
    wave = 0.5 * np.sin(2 * np.pi * hz * t).astype(np.float32)
    return AudioClip(np.stack([wave, wave]), sr)


def test_librosa_analyzer_extracts_key_and_notes():
    analysis = LibrosaAnalyzer().analyze(_tone(220.0), monophonic=True)  # A3
    assert analysis.duration == pytest.approx(3.0, abs=0.1)
    assert analysis.tempo_bpm >= 0  # tempo needs real rhythmic content; just confirm it runs
    assert analysis.notes_reliable is True
    # A steady A tone should yield A-pitched note events, and the key should be A.
    assert any(ev.pitch_class == "A" for ev in analysis.note_events)
    assert analysis.key.tonic == "A"


def test_librosa_analyzer_polyphonic_skips_notes():
    analysis = LibrosaAnalyzer().analyze(_tone(220.0), monophonic=False)
    assert analysis.notes_reliable is False
    assert analysis.note_events == []


def test_monophonic_classification():
    # Sanity: only bass/vocals are treated as monophonic by the session.
    from songstem.analysis.session import _MONOPHONIC

    assert _MONOPHONIC == {StemType.BASS, StemType.VOCALS}
