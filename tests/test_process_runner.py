"""Tests for the subprocess separation runner (run_jobs logic, called in-process)."""

import numpy as np

from songstem.audio import io
from songstem.models import AudioClip, SeparationJob, Song, StemType
from songstem.pipeline.process_runner import DONE, JobFailure, make_config, run_jobs
from songstem.separation.base import Separator
from songstem.separation.registry import register_backend


class _FakeSeparator(Separator):
    name = "faketest"

    @property
    def supported_stems(self) -> set[StemType]:
        return {StemType.BASS, StemType.DRUMS, StemType.VOCALS}

    def separate(self, mix: AudioClip) -> dict[StemType, AudioClip]:
        levels = {StemType.BASS: 0.1, StemType.DRUMS: 0.2, StemType.VOCALS: 0.3}
        return {
            s: AudioClip(np.full_like(mix.samples, v), mix.sample_rate)
            for s, v in levels.items()
        }


class _ListQueue:
    """Stand-in for the multiprocessing queue (run_jobs only ever calls put)."""

    def __init__(self):
        self.items = []

    def put(self, item):
        self.items.append(item)


def _job(tmp_path):
    src = io.save(AudioClip(np.zeros((2, 4096), dtype=np.float32), 44100), tmp_path / "in.wav")
    return SeparationJob(
        song=Song(title="T", artist="A", location=src),
        target=StemType.BASS,
        output_dir=tmp_path / "out",
    )


_CFG = {"backend": "faketest", "device": "cpu", "make_cheatsheet": False, "fetch_lyrics": False}


def test_run_jobs_streams_results_then_done(tmp_path):
    register_backend("faketest", _FakeSeparator)
    q = _ListQueue()
    run_jobs([_job(tmp_path)], _CFG, q)

    assert q.items[-1] == DONE
    results = [x for x in q.items if x != DONE]
    assert len(results) == 1
    assert results[0].ok and results[0].solo_path.exists()


def test_run_jobs_reports_backend_failure(tmp_path):
    q = _ListQueue()
    run_jobs([_job(tmp_path)], {**_CFG, "backend": "does-not-exist"}, q)

    assert any(isinstance(x, JobFailure) for x in q.items)
    assert q.items[-1] == DONE  # DONE is always sent, even after a failure


def test_make_config_extracts_picklable_subset():
    from songstem.config import Settings

    cfg = make_config(Settings())
    assert set(cfg) == {"backend", "device", "make_cheatsheet", "fetch_lyrics"}
