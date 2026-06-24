"""Drive iTunes playback over COM so a playlist can be re-recorded track by track.

`PlaybackController` is the seam the recording session depends on, so the batch loop can be
tested with `FakePlaybackController`. `ITunesPlaybackController` is the real Windows COM
implementation (`iTunes.Application`).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from songstem.models import Song

# iTunes ITPlayerState: 0 = stopped, 1 = playing.
_PLAYING = 1


@dataclass
class RecordableTrack:
    """A track that can be played for re-recording. `handle` is backend-specific."""

    song: Song
    duration: float  # seconds
    handle: object = None


class PlaybackController(ABC):
    @abstractmethod
    def playlist_tracks(self, playlist_name: str) -> list[RecordableTrack]: ...

    @abstractmethod
    def play(self, track: RecordableTrack) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...

    @abstractmethod
    def is_playing(self) -> bool: ...

    @abstractmethod
    def position(self) -> float:
        """Current playhead position in seconds."""


class ITunesPlaybackController(PlaybackController):
    def __init__(self) -> None:
        self._app = None

    def _connect(self):
        if self._app is None:
            import win32com.client

            self._app = win32com.client.Dispatch("iTunes.Application")
        return self._app

    def playlist_tracks(self, playlist_name: str) -> list[RecordableTrack]:
        app = self._connect()
        playlists = app.LibrarySource.Playlists
        tracks: list[RecordableTrack] = []
        for i in range(1, playlists.Count + 1):
            playlist = playlists.Item(i)
            if playlist.Name != playlist_name:
                continue
            com_tracks = playlist.Tracks
            for j in range(1, com_tracks.Count + 1):
                track = com_tracks.Item(j)
                tracks.append(
                    RecordableTrack(
                        song=Song(
                            title=track.Name or "",
                            artist=track.Artist or "",
                            album=track.Album or "",
                        ),
                        duration=float(track.Duration or 0),
                        handle=track,
                    )
                )
            break
        return tracks

    def play(self, track: RecordableTrack) -> None:
        self._connect()
        track.handle.Play()

    def stop(self) -> None:
        self._connect().Stop()

    def is_playing(self) -> bool:
        return self._connect().PlayerState == _PLAYING

    def position(self) -> float:
        return float(self._connect().PlayerPosition or 0)
