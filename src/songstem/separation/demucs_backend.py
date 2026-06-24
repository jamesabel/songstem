"""Default separation backend, built on Demucs (htdemucs_6s).

Demucs is imported lazily inside `separate` so the rest of the app — including the GUI and
the test suite — can run without the (large) ML stack installed.
"""

from __future__ import annotations

from songstem.models import AudioClip, StemType
from songstem.separation.base import Separator

# htdemucs_6s yields these six sources.
_DEMUCS_6S_STEMS = {
    StemType.DRUMS,
    StemType.BASS,
    StemType.OTHER,
    StemType.VOCALS,
    StemType.GUITAR,
    StemType.PIANO,
}


class DemucsSeparator(Separator):
    name = "demucs"

    def __init__(self, model_name: str = "htdemucs_6s", device: str = "cpu") -> None:
        self.model_name = model_name
        self.device = device  # "cpu" default; pass "cuda" when a GPU build is available
        self._model = None  # loaded on first use

    @property
    def supported_stems(self) -> set[StemType]:
        return set(_DEMUCS_6S_STEMS)

    def separate(self, mix: AudioClip) -> dict[StemType, AudioClip]:
        # TODO: lazy-load the Demucs model (demucs.pretrained.get_model), run
        # apply_model on `mix.samples`, and map each output source name to a StemType.
        raise NotImplementedError("Demucs separation not yet implemented")
