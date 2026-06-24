from pathlib import Path

from songstem.models import SeparationJob, Song, StemType
from songstem.utils.naming import output_filename, sanitize


def test_sanitize_strips_illegal_windows_chars():
    assert sanitize('a/b:c?d') == "a_b_c_d"


def test_sanitize_empty_falls_back():
    assert sanitize("   ") == "untitled"


def test_output_filename_includes_stem_and_variant():
    job = SeparationJob(
        song=Song(title="My Song", artist="The Band"),
        target=StemType.BASS,
        output_dir=Path("."),
    )
    assert output_filename(job, "solo") == "The Band - My Song [bass solo].wav"
    assert output_filename(job, "muted") == "The Band - My Song [bass muted].wav"
