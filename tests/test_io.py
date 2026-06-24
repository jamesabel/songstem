"""Audio I/O tests focused on DRM detection (no ffmpeg/soundfile needed for these)."""

from pathlib import Path

import pytest

from songstem.audio.io import DRMProtectedError, is_drm_protected, load


def test_is_drm_protected_detects_m4p():
    assert is_drm_protected(Path("song.m4p"))
    assert is_drm_protected(Path("SONG.M4P"))  # case-insensitive


def test_non_m4p_is_not_drm():
    for name in ("song.m4a", "song.mp3", "song.wav", "song.flac"):
        assert not is_drm_protected(Path(name))


def test_load_rejects_drm_with_clear_error():
    with pytest.raises(DRMProtectedError) as exc:
        load(Path("protected.m4p"))
    msg = str(exc.value)
    assert "DRM-protected" in msg and "FairPlay" in msg
