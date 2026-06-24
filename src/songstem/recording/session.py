"""Batch loopback re-recording: play each track and capture it to a WAV file.

The flow per track is: start the recorder a moment early (so the cable stream is warm),
start playback, wait for the track to finish, stop playback, let the tail drain, then stop
the recorder and write the buffer to disk. Timing hooks (`clock`, `sleep`) are injectable so
the loop can be unit-tested without real audio or iTunes.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from songstem.audio import io
from songstem.itunes.playback import PlaybackController, RecordableTrack
from songstem.models import AudioClip, Song
from songstem.recording.loopback import Recorder
from songstem.utils.naming import sanitize

# A capture below this peak amplitude is treated as silence — usually means the audio never
# reached the recording device (iTunes output not routed to CABLE Input, or RDP is redirecting
# remote audio to the client).
_SILENCE_PEAK = 1e-4
_SILENCE_HINT = (
    "captured silence — no audio reached the recording device. Route iTunes output to "
    "'CABLE Input'; if connected over RDP, set remote audio to play on the remote computer."
)

ProgressCallback = Callable[["RecordResult"], None]


@dataclass
class RecordResult:
    song: Song
    path: Path | None = None
    error: str | None = None
    silent: bool = False  # captured silence — signals the batch was aborted

    @property
    def ok(self) -> bool:
        return self.error is None


def wav_filename(song: Song) -> str:
    base = f"{sanitize(song.artist)} - {sanitize(song.title)}" if song.artist else sanitize(
        song.title
    )
    return f"{base}.wav"


def record_playlist(
    controller: PlaybackController,
    recorder: Recorder,
    playlist_name: str,
    output_dir: Path,
    on_result: ProgressCallback | None = None,
    *,
    lead_in: float = 0.3,
    tail: float = 0.5,
    poll: float = 0.1,
    startup_timeout: float = 5.0,
    max_overrun: float = 5.0,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    should_stop: Callable[[], bool] = lambda: False,
) -> list[RecordResult]:
    """Re-record every track of `playlist_name` to a WAV in `output_dir`.

    Per-track failures are captured in the returned RecordResult list rather than aborting
    the whole batch. `should_stop` is polled between tracks and during each track's playback;
    when it returns True the batch stops promptly and the in-progress track is not saved.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[RecordResult] = []
    for track in controller.playlist_tracks(playlist_name):
        if should_stop():
            break
        result = _record_one(
            controller, recorder, track, output_dir,
            lead_in=lead_in, tail=tail, poll=poll,
            startup_timeout=startup_timeout, max_overrun=max_overrun,
            clock=clock, sleep=sleep, should_stop=should_stop,
        )
        results.append(result)
        if on_result is not None:
            on_result(result)
        if result.silent:
            # A silent capture means audio isn't reaching the recorder (routing/RDP). Abort
            # rather than re-record the whole playlist into silence.
            break
    return results


def _record_one(
    controller, recorder, track: RecordableTrack, output_dir: Path, *,
    lead_in, tail, poll, startup_timeout, max_overrun, clock, sleep, should_stop,
) -> RecordResult:
    try:
        recorder.start()
        cancelled = False
        try:
            sleep(lead_in)
            controller.play(track)
            cancelled = _wait_for_track(
                controller, track.duration, poll, startup_timeout, max_overrun,
                clock, sleep, should_stop,
            )
            controller.stop()
            if not cancelled:
                sleep(tail)
        finally:
            clip = recorder.stop()
        if cancelled:
            return RecordResult(song=track.song, error="cancelled")
        if _peak(clip) < _SILENCE_PEAK:
            return RecordResult(song=track.song, error=_SILENCE_HINT, silent=True)
        path = io.save(clip, output_dir / wav_filename(track.song))
        return RecordResult(song=track.song, path=path)
    except Exception as exc:
        return RecordResult(song=track.song, error=str(exc))


def _peak(clip: AudioClip) -> float:
    return float(np.max(np.abs(clip.samples))) if clip.samples.size else 0.0


def _wait_for_track(
    controller, duration, poll, startup_timeout, max_overrun, clock, sleep, should_stop
) -> bool:
    """Wait for a track to finish. Returns True if interrupted via should_stop()."""
    # Wait for playback to actually begin (iTunes needs a moment to spin up).
    start = clock()
    while clock() - start < startup_timeout:
        if should_stop():
            return True
        if controller.is_playing():
            break
        sleep(poll)

    # Then wait for it to end — either iTunes reports stopped, or we exceed the known
    # duration plus a safety margin (in case the stopped state is missed).
    deadline = clock() + duration + max_overrun
    while clock() < deadline:
        if should_stop():
            return True
        if not controller.is_playing():
            return False
        sleep(poll)
    return False
