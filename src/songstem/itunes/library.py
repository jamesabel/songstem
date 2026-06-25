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
    """Windows COM-backed implementation (iTunes / Apple Music).

    iTunes COM collections are 1-indexed via `.Item(i)` over `.Count`; we use that rather
    than Python iteration for predictable behavior across pywin32 versions.
    """

    def __init__(self) -> None:
        self._app = None  # the iTunes.Application COM object, connected on first use

    def _connect(self):
        if self._app is None:
            # Imported lazily so non-Windows dev environments can import this module.
            import win32com.client

            self._app = win32com.client.Dispatch("iTunes.Application")
        return self._app

    def _playlists(self):
        return self._connect().LibrarySource.Playlists

    def playlist_names(self) -> list[str]:
        playlists = self._playlists()
        return [playlists.Item(i).Name for i in range(1, playlists.Count + 1)]

    def songs_in_playlist(self, name: str) -> list[Song]:
        playlists = self._playlists()
        playlist = None
        for i in range(1, playlists.Count + 1):
            candidate = playlists.Item(i)
            if candidate.Name == name:
                playlist = candidate
                break
        if playlist is None:
            return []

        songs: list[Song] = []
        tracks = playlist.Tracks
        # ItemByPlayOrder yields the playlist's displayed order (honoring any column sort);
        # Item(i) is iTunes' internal database order, which can differ.
        for i in range(1, tracks.Count + 1):
            track = tracks.ItemByPlayOrder(i)
            songs.append(_track_to_song(track))
        return songs


def _track_to_song(track) -> Song:
    """Map an iTunes COM track object to a Song, tolerating missing fields."""
    # Location is empty for cloud-only tracks and can raise for stream/URL tracks.
    try:
        location = track.Location
    except Exception:
        location = None
    persistent_id = ""
    try:
        persistent_id = str(track.TrackDatabaseID)
    except Exception:
        pass
    return Song(
        title=track.Name or "",
        artist=track.Artist or "",
        album=track.Album or "",
        location=Path(location) if location else None,
        persistent_id=persistent_id,
    )


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
