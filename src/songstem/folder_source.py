"""A LibrarySource backed by a folder of audio files.

Lets songstem consume audio that isn't in iTunes — e.g. the WAVs produced by loopback
re-recording, CD rips, or downloaded DRM-free files. The folder is presented as a single
"playlist" named after the folder.
"""

from __future__ import annotations

from pathlib import Path

from songstem.itunes.library import LibrarySource
from songstem.models import Song

# Formats songstem can decode (DRM-free containers). `.m4p` is intentionally excluded.
AUDIO_SUFFIXES = {".wav", ".flac", ".mp3", ".m4a", ".aif", ".aiff", ".ogg"}


class FolderLibrary(LibrarySource):
    """Exposes the audio files in a directory as one playlist."""

    def __init__(self, folder: Path) -> None:
        self.folder = Path(folder)

    def playlist_names(self) -> list[str]:
        return [self.folder.name]

    def songs_in_playlist(self, name: str) -> list[Song]:
        if name != self.folder.name or not self.folder.is_dir():
            return []
        files = [
            p
            for p in self.folder.iterdir()
            if p.is_file() and p.suffix.lower() in AUDIO_SUFFIXES
        ]
        # Order by modification time so re-recorded folders keep the playlist's order (files
        # are written track by track), rather than alphabetically.
        files.sort(key=lambda p: p.stat().st_mtime)
        return [Song(title=p.stem, artist="", location=p) for p in files]
