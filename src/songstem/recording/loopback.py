"""Capture audio from the VB-Audio virtual cable into an AudioClip.

Setup (one-time, by the user): install VB-Audio Virtual Cable, set the system (or iTunes')
playback device to **CABLE Input**, so everything iTunes plays is routed into the cable. This
recorder reads the other end of the cable, **CABLE Output**, an input/recording device.

`sounddevice` (PortAudio) is imported lazily so the rest of the app imports without an audio
backend present.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from songstem.models import AudioClip

# The recording endpoint VB-Audio Virtual Cable exposes; matched case-insensitively.
VB_AUDIO_OUTPUT_NAME = "CABLE Output"


class LoopbackError(RuntimeError):
    """Raised when the loopback capture device is missing or capture fails."""


class Recorder(ABC):
    """Records whatever is playing and returns it as an AudioClip."""

    @abstractmethod
    def start(self) -> None:
        """Begin capturing into an internal buffer."""

    @abstractmethod
    def stop(self) -> AudioClip:
        """Stop capturing and return everything recorded since start()."""


def find_input_device(name_substr: str = VB_AUDIO_OUTPUT_NAME) -> int:
    """Return the device index of the first input device whose name contains `name_substr`.

    Raises LoopbackError (listing available inputs) if none match — usually means VB-Audio
    Virtual Cable is not installed.
    """
    import sounddevice as sd

    inputs = []
    for index, device in enumerate(sd.query_devices()):
        if device["max_input_channels"] > 0:
            inputs.append(device["name"])
            if name_substr.lower() in device["name"].lower():
                return index
    raise LoopbackError(
        f"No input device matching {name_substr!r} found. Install VB-Audio Virtual Cable "
        f"and route iTunes output to 'CABLE Input'. Available inputs: {inputs}"
    )


class LoopbackRecorder(Recorder):
    """Records from a VB-Audio (or named) input device via sounddevice."""

    def __init__(
        self,
        device_name: str = VB_AUDIO_OUTPUT_NAME,
        sample_rate: int | None = None,
        channels: int = 2,
    ) -> None:
        self.device_name = device_name
        self.channels = channels
        self._requested_rate = sample_rate
        self._stream = None
        self._blocks: list[np.ndarray] = []
        self._sample_rate = sample_rate or 44100

    def start(self) -> None:
        import sounddevice as sd

        device = find_input_device(self.device_name)
        # Use the device's native rate unless the caller forced one.
        rate = self._requested_rate or int(sd.query_devices(device)["default_samplerate"])
        self._sample_rate = rate
        self._blocks = []

        def callback(indata, _frames, _time, status):  # called on the audio thread
            if status:  # overflow/underflow — keep going, the data is still usable
                pass
            self._blocks.append(indata.copy())

        self._stream = sd.InputStream(
            device=device,
            channels=self.channels,
            samplerate=rate,
            dtype="float32",
            callback=callback,
        )
        self._stream.start()

    def stop(self) -> AudioClip:
        if self._stream is None:
            raise LoopbackError("stop() called before start()")
        self._stream.stop()
        self._stream.close()
        self._stream = None

        if self._blocks:
            data = np.concatenate(self._blocks, axis=0)  # (frames, channels)
        else:
            data = np.zeros((0, self.channels), dtype=np.float32)
        return AudioClip(samples=data.T.copy(), sample_rate=self._sample_rate)
