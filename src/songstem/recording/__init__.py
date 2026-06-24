"""Loopback re-recording of playlists into DRM-free WAV files.

For personal use only. This captures audio as it plays through a virtual audio device
(VB-Audio Virtual Cable) — it records playback output, it does not decrypt or remove DRM.
"""

from songstem.recording.loopback import LoopbackError, LoopbackRecorder, Recorder
from songstem.recording.session import RecordResult, record_playlist

__all__ = ["LoopbackError", "LoopbackRecorder", "Recorder", "RecordResult", "record_playlist"]
