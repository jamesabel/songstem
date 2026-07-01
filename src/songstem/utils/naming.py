"""Filesystem-safe output filenames for generated stem files."""

from __future__ import annotations

import re
from pathlib import Path

from songstem.models import SeparationJob, Song

_UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def sanitize(text: str) -> str:
    """Strip characters Windows disallows in filenames; collapse whitespace."""
    cleaned = _UNSAFE.sub("_", text).strip()
    return re.sub(r"\s+", " ", cleaned) or "untitled"


def _base_name(song: Song) -> str:
    artist = sanitize(song.artist) if song.artist else ""
    title = sanitize(song.title)
    return f"{artist} - {title}" if artist else title


def output_filename(job: SeparationJob, variant: str) -> str:
    """e.g. 'Artist - Title [bass solo].wav'."""
    return f"{_base_name(job.song)} [{job.target.value} {variant}].wav"


def cheatsheet_filename(song: Song, stem: str) -> str:
    """e.g. 'Artist - Title [bass cheatsheet].md'."""
    return f"{_base_name(song)} [{stem} cheatsheet].md"


def pitch_shift_suffix(semitones: int) -> str:
    """The half-step suffix embedded in pitch-shifted filenames, e.g. '[+2st]' / '[-1st]'."""
    return f"[{semitones:+d}st]"


def pitch_shifted_filename(source: Path, semitones: int) -> str:
    """Name of the pitch-shifted copy of `source`, e.g. 'Artist - Title [+2st].wav'.

    Derived from the source file's stem (not a Song) so it sits next to the source and keeps
    whatever name the source already has, regardless of how its metadata was resolved.
    """
    return f"{source.stem} {pitch_shift_suffix(semitones)}.wav"
