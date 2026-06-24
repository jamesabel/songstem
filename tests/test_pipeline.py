"""End-to-end pipeline test using a fake separator (no ML model download).

Exercises BatchProcessor + mixer + audio.io + naming against real files on disk.
"""

import numpy as np

from songstem.audio import io
from songstem.models import AudioClip, SeparationJob, Song, StemType
from songstem.pipeline import BatchProcessor
from songstem.separation.base import Separator


class FakeSeparator(Separator):
    name = "fake"

    @property
    def supported_stems(self) -> set[StemType]:
        return {StemType.BASS, StemType.DRUMS, StemType.VOCALS}

    def separate(self, mix: AudioClip) -> dict[StemType, AudioClip]:
        # Deterministic, distinct constant level per stem.
        levels = {StemType.BASS: 0.1, StemType.DRUMS: 0.2, StemType.VOCALS: 0.3}
        return {
            stem: AudioClip(
                samples=np.full_like(mix.samples, level), sample_rate=mix.sample_rate
            )
            for stem, level in levels.items()
        }


def _write_input(path):
    clip = AudioClip(samples=np.zeros((2, 4096), dtype=np.float32), sample_rate=44100)
    return io.save(clip, path)


def test_batch_produces_solo_and_muted_files(tmp_path):
    src = _write_input(tmp_path / "input.wav")
    out_dir = tmp_path / "out"
    job = SeparationJob(
        song=Song(title="Track", artist="Artist", location=src),
        target=StemType.BASS,
        output_dir=out_dir,
    )

    results = BatchProcessor(FakeSeparator()).run([job])

    assert len(results) == 1
    result = results[0]
    assert result.ok, result.error
    assert result.solo_path.exists()
    assert result.muted_path.exists()

    solo = io.load(result.solo_path)
    muted = io.load(result.muted_path)
    assert np.allclose(solo.samples, 0.1, atol=1e-4)  # isolated bass
    assert np.allclose(muted.samples, 0.2 + 0.3, atol=1e-4)  # drums + vocals, no bass


def test_cloud_only_song_reports_error():
    job = SeparationJob(
        song=Song(title="Cloud", artist="X", location=None),
        target=StemType.BASS,
        output_dir=None,
    )
    [result] = BatchProcessor(FakeSeparator()).run([job])
    assert not result.ok
    assert "cloud-only" in result.error
