"""Build the two outputs of the app from a set of separated stems.

- solo  : the target stem on its own.
- muted : the sum of all *other* stems, each scaled by an optional per-stem gain.

Pure NumPy and dependency-light so it is easy to unit test.
"""

from __future__ import annotations

import numpy as np

from songstem.models import AudioClip, StemType


def build_solo(stems: dict[StemType, AudioClip], target: StemType) -> AudioClip:
    if target not in stems:
        raise KeyError(f"target stem {target} not present in {sorted(stems)}")
    clip = stems[target]
    return AudioClip(samples=clip.samples.copy(), sample_rate=clip.sample_rate)


def build_muted_mix(
    stems: dict[StemType, AudioClip],
    target: StemType,
    gains: dict[StemType, float] | None = None,
) -> AudioClip:
    """Sum every stem except `target`, applying per-stem `gains` (default 1.0)."""
    if target not in stems:
        raise KeyError(f"target stem {target} not present in {sorted(stems)}")
    gains = gains or {}

    sample_rate = next(iter(stems.values())).sample_rate
    shape = next(iter(stems.values())).samples.shape
    acc = np.zeros(shape, dtype=np.float32)
    for stem, clip in stems.items():
        if stem == target:
            continue
        acc += clip.samples * float(gains.get(stem, 1.0))

    np.clip(acc, -1.0, 1.0, out=acc)
    return AudioClip(samples=acc, sample_rate=sample_rate)
