from pathlib import Path

from songstem.models import SeparationJob, Song, StemType
from songstem.utils.naming import (
    cheatsheet_filename,
    output_filename,
    pitch_shifted_filename,
    sanitize,
)


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


def test_cheatsheet_filename():
    song = Song(title="My Song", artist="The Band")
    assert cheatsheet_filename(song, "bass") == "The Band - My Song [bass cheatsheet].md"


def test_pitch_shifted_filename_encodes_sign():
    src = Path("The Band - My Song.wav")
    assert pitch_shifted_filename(src, 2) == "The Band - My Song [+2st].wav"
    assert pitch_shifted_filename(src, -1) == "The Band - My Song [-1st].wav"
