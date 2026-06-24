"""The separation backend contract.

Adding a new engine (Open-Unmix, Spleeter, a future model, ...) means implementing
`Separator` and registering it — nothing else in the app should need to change.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from songstem.models import AudioClip, StemType


class Separator(ABC):
    """Splits a mixed `AudioClip` into its constituent stems."""

    #: Stable identifier used in settings and the registry (e.g. "demucs").
    name: str = ""

    @property
    @abstractmethod
    def supported_stems(self) -> set[StemType]:
        """Stems this backend can isolate."""

    @abstractmethod
    def separate(self, mix: AudioClip) -> dict[StemType, AudioClip]:
        """Separate `mix` into stems.

        Returns a mapping containing exactly `supported_stems`. Every returned clip shares
        the input's sample rate, channel count, and frame count so they can be summed
        directly by the mixer.
        """
