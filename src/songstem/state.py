"""SQLite-backed persistence of GUI selection state via the `pref` library.

Remembers the last-selected playlist and, per playlist, which songs were checked, so the
selection is restored when the app is relaunched. Data lives in a local SQLite database under
the user's app-data directory (managed by `pref`); pass `file_name` to redirect it — used in
tests.

`PrefOrderedSet.get(default=None)` returns the default only when the set was never written, so
"never touched → select all songs by default" stays cleanly distinct from "user unchecked
everything → restore the empty selection". Each access is wrapped in a context manager so the
underlying SQLite handles are closed promptly.
"""

from __future__ import annotations

import hashlib

from attr import attrib, attrs
from pref import Pref, PrefStore

from songstem.config import APP_AUTHOR, APP_NAME
from songstem.models import Song

# Unit separator keeps the artist/title fallback key unambiguous.
_SEP = "\x1f"


def song_key(song: Song) -> str:
    """Stable identity for a song's selection state across relaunches.

    Prefers the iTunes persistent/database id; falls back to artist+title.
    """
    if song.persistent_id:
        return f"id:{song.persistent_id}"
    return f"name:{song.artist}{_SEP}{song.title}"


@attrs
class _GeneralPref(Pref):
    selected_playlist: str = attrib(default="")


def _songs_table(playlist: str) -> str:
    # Hash so arbitrary playlist names map to safe, fixed-length SQL table identifiers.
    digest = hashlib.sha1(playlist.encode("utf-8")).hexdigest()[:16]
    return f"songs_{digest}"


class UiStateStore:
    """Reads/writes UI selection state. Every write persists immediately to SQLite."""

    def __init__(self, file_name: str | None = None) -> None:
        self._store = PrefStore(APP_NAME, APP_AUTHOR, file_name)
        self._general = self._store.bind(_GeneralPref)

    # selected playlist -------------------------------------------------

    @property
    def selected_playlist(self) -> str:
        return self._general.selected_playlist

    @selected_playlist.setter
    def selected_playlist(self, name: str) -> None:
        self._general.selected_playlist = name

    # selected songs per playlist --------------------------------------

    def get_selected_songs(self, playlist: str) -> list[str] | None:
        """Saved checked-song keys for `playlist`, or None if it was never saved."""
        if not playlist:
            return None
        with self._store.ordered_set(_songs_table(playlist)) as songs:
            return songs.get(default=None)

    def set_selected_songs(self, playlist: str, keys: list[str]) -> None:
        if not playlist:
            return
        with self._store.ordered_set(_songs_table(playlist)) as songs:
            songs.set(keys)
