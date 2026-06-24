"""Loopback recording tests — batch orchestration with fakes, plus device matching."""

import numpy as np
import pytest

from songstem.audio import io
from songstem.itunes.playback import PlaybackController, RecordableTrack
from songstem.models import AudioClip, Song
from songstem.recording.loopback import LoopbackError, Recorder, find_input_device
from songstem.recording.session import record_playlist, wav_filename


class FakeController(PlaybackController):
    """Simulates iTunes: each track 'plays' for a fixed number of poll cycles."""

    def __init__(self, tracks, plays_for=3):
        self._tracks = tracks
        self._plays_for = plays_for
        self._remaining = 0
        self.played = []

    def playlist_tracks(self, playlist_name):
        return list(self._tracks)

    def play(self, track):
        self.played.append(track.song.title)
        self._remaining = self._plays_for

    def stop(self):
        self._remaining = 0

    def is_playing(self):
        if self._remaining > 0:
            self._remaining -= 1
            return True
        return False

    def position(self):
        return 0.0


class FakeRecorder(Recorder):
    def __init__(self, level=0.5):
        self.calls = []
        self._level = level

    def start(self):
        self.calls.append("start")

    def stop(self):
        self.calls.append("stop")
        samples = np.full((2, 1024), self._level, dtype=np.float32)
        return AudioClip(samples=samples, sample_rate=44100)


def _tracks():
    return [
        RecordableTrack(song=Song(title="One", artist="A"), duration=1.0),
        RecordableTrack(song=Song(title="Two", artist="B"), duration=1.0),
    ]


def test_wav_filename_is_sanitized():
    assert wav_filename(Song(title="A/B", artist="X")) == "X - A_B.wav"
    assert wav_filename(Song(title="No Artist", artist="")) == "No Artist.wav"


def test_record_playlist_writes_one_wav_per_track(tmp_path):
    controller = FakeController(_tracks())
    recorder = FakeRecorder()
    results = record_playlist(
        controller, recorder, "P", tmp_path, sleep=lambda _s: None
    )

    assert [r.song.title for r in results] == ["One", "Two"]
    assert all(r.ok for r in results)
    assert controller.played == ["One", "Two"]
    files = sorted(p.name for p in tmp_path.glob("*.wav"))
    assert files == ["A - One.wav", "B - Two.wav"]
    # Each recorded file is loadable.
    assert io.load(results[0].path).sample_rate == 44100


def test_silent_capture_aborts_batch(tmp_path):
    # A silent recording (no audio reached the device, e.g. RDP redirection) aborts the whole
    # batch after the first track, writes no WAV, and is flagged silent.
    controller = FakeController(_tracks())  # two tracks
    results = record_playlist(
        controller, FakeRecorder(level=0.0), "P", tmp_path, sleep=lambda _s: None
    )
    assert len(results) == 1  # stopped after the first silent capture
    assert results[0].silent is True
    assert "silence" in results[0].error
    assert controller.played == ["One"]  # second track was never played
    assert list(tmp_path.glob("*.wav")) == []


def test_should_stop_halts_between_tracks(tmp_path):
    seen = {"n": 0}

    def on_result(_r):
        seen["n"] += 1

    results = record_playlist(
        FakeController(_tracks()),
        FakeRecorder(),
        "P",
        tmp_path,
        on_result=on_result,
        sleep=lambda _s: None,
        should_stop=lambda: seen["n"] >= 1,  # stop once the first track is done
    )
    assert len(results) == 1
    assert results[0].song.title == "One"


def test_should_stop_cancels_current_track(tmp_path):
    calls = {"n": 0}

    def should_stop():
        calls["n"] += 1
        return calls["n"] > 1  # False at the loop guard, True once inside the wait

    results = record_playlist(
        FakeController(_tracks()), FakeRecorder(), "P", tmp_path,
        sleep=lambda _s: None, should_stop=should_stop,
    )
    assert len(results) == 1
    assert results[0].error == "cancelled"
    assert list(tmp_path.glob("*.wav")) == []  # partial track not saved


def test_record_playlist_reports_per_track_errors(tmp_path):
    class Boom(FakeRecorder):
        def stop(self):
            raise RuntimeError("device gone")

    results = record_playlist(
        FakeController(_tracks()), Boom(), "P", tmp_path, sleep=lambda _s: None
    )
    assert all(not r.ok for r in results)
    assert "device gone" in results[0].error


def _fake_sounddevice(devices):
    # find_input_device imports `sounddevice` locally, so patch it in sys.modules.
    return type("sd", (), {"query_devices": staticmethod(lambda: devices)})


def test_find_input_device_matches_substring(monkeypatch):
    import sys

    devices = [
        {"name": "Speakers", "max_input_channels": 0},
        {"name": "CABLE Output (VB-Audio Virtual Cable)", "max_input_channels": 2},
    ]
    monkeypatch.setitem(sys.modules, "sounddevice", _fake_sounddevice(devices))
    assert find_input_device("CABLE Output") == 1


def test_find_input_device_raises_when_missing(monkeypatch):
    import sys

    devices = [{"name": "Mic", "max_input_channels": 1}]
    monkeypatch.setitem(sys.modules, "sounddevice", _fake_sounddevice(devices))
    with pytest.raises(LoopbackError):
        find_input_device("CABLE Output")
