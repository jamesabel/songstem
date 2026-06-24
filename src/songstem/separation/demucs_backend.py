"""Default separation backend, built on Demucs (htdemucs_6s).

Torch and Demucs are imported lazily inside the methods that use them so the rest of the
app — including the GUI and the test suite — can run without the (large) ML stack loaded.
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

    def _load_model(self):
        if self._model is None:
            from demucs.pretrained import get_model

            model = get_model(self.model_name)  # downloads + caches on first call
            model.to(self.device)
            model.eval()
            self._model = model
        return self._model

    def separate(self, mix: AudioClip) -> dict[StemType, AudioClip]:
        import numpy as np
        import torch
        from demucs.apply import apply_model
        from demucs.audio import convert_audio

        model = self._load_model()

        wav = torch.from_numpy(np.ascontiguousarray(mix.samples)).to(torch.float32)
        # Demucs expects (channels, length) at the model's sample rate / channel count.
        wav = convert_audio(wav, mix.sample_rate, model.samplerate, model.audio_channels)

        # Standardize then restore scale, mirroring demucs.separate.
        ref = wav.mean(0)
        std = ref.std() + 1e-8
        wav = (wav - ref.mean()) / std
        with torch.no_grad():
            est = apply_model(model, wav[None], device=self.device, progress=False)[0]
        est = est * std + ref.mean()

        stems: dict[StemType, AudioClip] = {}
        for name, source in zip(model.sources, est):
            stems[StemType(name)] = AudioClip(
                samples=source.cpu().numpy().astype("float32"),
                sample_rate=model.samplerate,
            )
        return stems
