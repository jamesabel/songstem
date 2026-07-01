"""Pitch-shift tests — the librosa-backed primitive plus the batch loop with fakes."""

import numpy as np

from songstem.audio import io
from songstem.audio.pitch import PitchShiftResult, shift_pitch, shift_songs
from songstem.models import AudioClip, Song


def _sine(freq=220.0, seconds=0.5, sr=22050, channels=2):
    t = np.linspace(0.0, seconds, int(seconds * sr), endpoint=False, dtype=np.float32)
    wave = (0.5 * np.sin(2 * np.pi * freq * t)).astype(np.float32)
    return AudioClip(samples=np.stack([wave] * channels), sample_rate=sr)


def test_shift_pitch_preserves_shape_and_rate():
    clip = _sine()
    out = shift_pitch(clip, 2)
    assert out.samples.shape == clip.samples.shape
    assert out.sample_rate == clip.sample_rate
    assert out.samples.dtype == np.float32
    # A real transpose changes the waveform.
    assert not np.allclose(out.samples, clip.samples)


def test_shift_pitch_zero_is_noop():
    clip = _sine()
    assert shift_pitch(clip, 0) is clip


def _fake_shift(clip, semitones):
    return clip  # identity — keeps the batch loop independent of librosa


def _items(tmp_path):
    src = tmp_path / "The Band - My Song.wav"
    io.save(_sine(), src)
    return [(Song(title="My Song", artist="The Band"), src, 2)]


def test_shift_songs_writes_suffixed_wav(tmp_path):
    results = shift_songs(_items(tmp_path), shift=_fake_shift)
    assert len(results) == 1 and results[0].ok
    out = results[0].path
    assert out.name == "The Band - My Song [+2st].wav"
    assert out.exists()
    assert io.load(out).sample_rate == 22050  # readable


def test_shift_songs_negative_suffix(tmp_path):
    src = tmp_path / "Solo.wav"
    io.save(_sine(), src)
    results = shift_songs([(Song(title="Solo", artist=""), src, -1)], shift=_fake_shift)
    assert results[0].path.name == "Solo [-1st].wav"


def test_shift_songs_reports_per_item_errors(tmp_path):
    def boom(clip, semitones):
        raise RuntimeError("no dsp")

    seen = []
    results = shift_songs(
        _items(tmp_path), shift=boom, on_result=seen.append
    )
    assert not results[0].ok
    assert "no dsp" in results[0].error
    assert seen == results  # on_result fired per item


def test_shift_songs_should_stop_halts(tmp_path):
    a = tmp_path / "A - One.wav"
    b = tmp_path / "B - Two.wav"
    io.save(_sine(), a)
    io.save(_sine(), b)
    items = [
        (Song(title="One", artist="A"), a, 1),
        (Song(title="Two", artist="B"), b, 1),
    ]
    calls = {"n": 0}

    def should_stop():
        calls["n"] += 1
        return calls["n"] > 1  # allow the first item, stop before the second

    results = shift_songs(items, shift=_fake_shift, should_stop=should_stop)
    assert [r.song.title for r in results] == ["One"]
    assert isinstance(results[0], PitchShiftResult)
