"""Filesystem-safe output filenames for generated stem files."""

from __future__ import annotations

import re

from songstem.models import SeparationJob

_UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def sanitize(text: str) -> str:
    """Strip characters Windows disallows in filenames; collapse whitespace."""
    cleaned = _UNSAFE.sub("_", text).strip()
    return re.sub(r"\s+", " ", cleaned) or "untitled"


def output_filename(job: SeparationJob, variant: str) -> str:
    """e.g. 'Artist - Title [bass solo].wav'."""
    song = job.song
    stem = job.target.value
    artist = sanitize(song.artist) if song.artist else ""
    title = sanitize(song.title)
    base = f"{artist} - {title}" if artist else title
    return f"{base} [{stem} {variant}].wav"
