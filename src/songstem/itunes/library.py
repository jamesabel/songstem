"""Read playlists and tracks from Apple Music / iTunes.

`LibrarySource` is the abstraction the rest of the app depends on, so the GUI and pipeline
never touch COM directly and can be exercised with a fake source in tests. `ITunesLibrary`
is the concrete Windows implementation via the `iTunes.Application` COM object (pywin32).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from songstem.models import Song


class LibrarySource(ABC):
    """Provides playlists and their songs."""

    @abstractmethod
    def playlist_names(self) -> list[str]:
        """All user playlist names."""

    @abstractmethod
    def songs_in_playlist(self, name: str) -> list[Song]:
        """Tracks in the named playlist, in playlist order."""


class ITunesLibrary(LibrarySource):
    """Windows COM-backed implementation (iTunes / Apple Music)."""

    def __init__(self) -> None:
        self._app = None  # the iTunes.Application COM object, connected on first use

    def _connect(self):
        if self._app is None:
            # TODO: import win32com.client and dispatch "iTunes.Application".
            # Kept lazy so non-Windows dev environments can import this module.
            raise NotImplementedError("iTunes COM connection not yet implemented")
        return self._app

    def playlist_names(self) -> list[str]:
        # TODO: iterate app.LibrarySource.Playlists, return .Name for each.
        raise NotImplementedError

    def songs_in_playlist(self, name: str) -> list[Song]:
        # TODO: locate the playlist, iterate Tracks, map to Song(...). Track.Location
        # gives the local file path (may be empty for cloud-only tracks).
        raise NotImplementedError


class FakeLibrary(LibrarySource):
    """In-memory source for development and tests."""

    def __init__(self, playlists: dict[str, list[Song]] | None = None) -> None:
        self._playlists = playlists or {}

    def playlist_names(self) -> list[str]:
        return list(self._playlists)

    def songs_in_playlist(self, name: str) -> list[Song]:
        return list(self._playlists.get(name, []))


def default_source() -> LibrarySource:
    """The source to use at runtime on the target (Windows) platform."""
    return ITunesLibrary()
