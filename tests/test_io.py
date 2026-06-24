"""Audio I/O tests: DRM detection, audio-content probe, and atomic save."""

from pathlib import Path

import numpy as np
import pytest

from songstem.audio.io import (
    DRMProtectedError,
    has_audio_content,
    is_drm_protected,
    load,
    save_atomic,
)
from songstem.models import AudioClip


def _clip(seconds, level=0.5, sr=8000):
    return AudioClip(np.full((2, int(seconds * sr)), level, dtype=np.float32), sr)


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


def test_has_audio_content(tmp_path):
    save_atomic(_clip(2.0), tmp_path / "ok.wav")
    save_atomic(_clip(2.0, level=0.0), tmp_path / "silent.wav")
    save_atomic(_clip(0.3), tmp_path / "short.wav")

    assert has_audio_content(tmp_path / "ok.wav", min_seconds=1.0)
    assert not has_audio_content(tmp_path / "silent.wav", min_seconds=1.0)  # silent
    assert not has_audio_content(tmp_path / "short.wav", min_seconds=1.0)  # too short
    assert not has_audio_content(tmp_path / "missing.wav", min_seconds=1.0)


def test_save_atomic_writes_complete_file_no_temp_left(tmp_path):
    dest = tmp_path / "out.wav"
    save_atomic(_clip(1.0), dest)
    assert dest.exists()
    assert load(dest).duration_seconds == pytest.approx(1.0, abs=0.01)
    assert list(tmp_path.glob("*.tmp")) == []  # temp cleaned up


def test_save_atomic_leaves_no_partial_on_failure(tmp_path, monkeypatch):
    import soundfile as sf

    monkeypatch.setattr(sf, "write", lambda *a, **k: (_ for _ in ()).throw(OSError("disk full")))
    dest = tmp_path / "out.wav"
    with pytest.raises(OSError):
        save_atomic(_clip(1.0), dest)
    assert not dest.exists()  # destination never half-written
    assert list(tmp_path.glob("*.tmp")) == []  # temp cleaned up
