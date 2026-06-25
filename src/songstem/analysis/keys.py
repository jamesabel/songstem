"""Musical key estimation via the Krumhansl–Schmuckler algorithm.

Pure NumPy: given a 12-bin chroma vector (average energy per pitch class), correlate it against
the 24 rotated major/minor key profiles and pick the best match. Testable from a synthetic
chroma vector — the librosa chroma extraction lives in `analyzer`, not here.
"""

from __future__ import annotations

import numpy as np

from songstem.analysis.models import PITCH_CLASSES, KeyEstimate

# Krumhansl–Kessler key profiles (relative tonal-hierarchy weights).
_MAJOR_PROFILE = np.array(
    [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
)
_MINOR_PROFILE = np.array(
    [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
)

_MAJOR_INTERVALS = [0, 2, 4, 5, 7, 9, 11]
_NATURAL_MINOR_INTERVALS = [0, 2, 3, 5, 7, 8, 10]


def _pearson(a: np.ndarray, b: np.ndarray) -> float:
    a = a - a.mean()
    b = b - b.mean()
    denom = np.sqrt((a * a).sum() * (b * b).sum())
    return float((a * b).sum() / denom) if denom else 0.0


def estimate_key(chroma_mean: np.ndarray) -> KeyEstimate:
    """Estimate the key from a 12-element chroma vector (index 0 = C)."""
    chroma = np.asarray(chroma_mean, dtype=float).reshape(12)
    best = KeyEstimate(tonic="C", mode="major", confidence=-1.0)
    for tonic in range(12):
        for mode, profile in (("major", _MAJOR_PROFILE), ("minor", _MINOR_PROFILE)):
            score = _pearson(chroma, np.roll(profile, tonic))
            if score > best.confidence:
                best = KeyEstimate(PITCH_CLASSES[tonic], mode, score)
    return best


def scale_notes(key: KeyEstimate) -> list[str]:
    """The seven diatonic pitch classes of `key` (major or natural minor)."""
    tonic = PITCH_CLASSES.index(key.tonic)
    intervals = _MAJOR_INTERVALS if key.mode == "major" else _NATURAL_MINOR_INTERVALS
    return [PITCH_CLASSES[(tonic + i) % 12] for i in intervals]
