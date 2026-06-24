"""Tests for song-source resolution (which drives Song List greying)."""

from songstem.gui.main_window import resolve_source
from songstem.models import Song


def test_drm_free_original_is_used(tmp_path):
    f = tmp_path / "song.mp3"
    f.write_bytes(b"x")
    song = Song(title="T", artist="A", location=f)
    assert resolve_source(song, tmp_path / "recordings") == f


def test_missing_original_file_is_not_used(tmp_path):
    song = Song(title="T", artist="A", location=tmp_path / "gone.mp3")
    assert resolve_source(song, tmp_path / "recordings") is None


def test_drm_falls_back_to_rerecorded_wav(tmp_path):
    rec = tmp_path / "recordings"
    rec.mkdir()
    (rec / "A - T.wav").write_bytes(b"x")  # matches wav_filename(song)
    song = Song(title="T", artist="A", location=tmp_path / "05 T.m4p")  # DRM
    assert resolve_source(song, rec) == rec / "A - T.wav"


def test_drm_without_wav_is_unavailable(tmp_path):
    song = Song(title="T", artist="A", location=tmp_path / "05 T.m4p")  # DRM, no wav
    assert resolve_source(song, tmp_path / "recordings") is None


def test_cloud_only_without_wav_is_unavailable(tmp_path):
    song = Song(title="T", artist="A", location=None)
    assert resolve_source(song, tmp_path / "recordings") is None


def test_cloud_only_with_wav_is_available(tmp_path):
    rec = tmp_path / "recordings"
    rec.mkdir()
    wav = rec / "A - T.wav"
    wav.write_bytes(b"x")
    song = Song(title="T", artist="A", location=None)
    assert resolve_source(song, rec) == wav
