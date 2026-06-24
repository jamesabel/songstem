import numpy as np

from songstem.audio import mixer
from songstem.models import AudioClip, StemType


def _clip(value: float, frames: int = 4) -> AudioClip:
    return AudioClip(samples=np.full((2, frames), value, dtype=np.float32), sample_rate=44100)


def _stems() -> dict[StemType, AudioClip]:
    return {
        StemType.BASS: _clip(0.1),
        StemType.DRUMS: _clip(0.2),
        StemType.VOCALS: _clip(0.3),
    }


def test_solo_returns_copy_of_target():
    stems = _stems()
    solo = mixer.build_solo(stems, StemType.BASS)
    assert np.allclose(solo.samples, 0.1)
    solo.samples[:] = 0.9
    assert np.allclose(stems[StemType.BASS].samples, 0.1)  # original untouched


def test_muted_sums_all_but_target():
    muted = mixer.build_muted_mix(_stems(), StemType.BASS)
    assert np.allclose(muted.samples, 0.2 + 0.3)


def test_muted_applies_per_stem_gain():
    muted = mixer.build_muted_mix(_stems(), StemType.BASS, gains={StemType.DRUMS: 0.0})
    assert np.allclose(muted.samples, 0.3)  # drums silenced, vocals remain


def test_muted_clips_to_unit_range():
    stems = {StemType.BASS: _clip(0.1), StemType.DRUMS: _clip(0.8), StemType.VOCALS: _clip(0.8)}
    muted = mixer.build_muted_mix(stems, StemType.BASS)
    assert muted.samples.max() <= 1.0
