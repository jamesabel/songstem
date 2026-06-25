"""FolderLibrary tests — exposing a folder of audio files as a playlist."""

import os

from songstem.folder_source import FolderLibrary


def _touch(path, mtime):
    path.write_bytes(b"")
    os.utime(path, (mtime, mtime))


def test_lists_audio_in_recording_order_not_alphabetical(tmp_path):
    # Files recorded out of alphabetical order: "zebra" first, "apple" later.
    _touch(tmp_path / "zebra.wav", mtime=1000)
    _touch(tmp_path / "apple.mp3", mtime=2000)
    (tmp_path / "notes.txt").write_bytes(b"")  # ignored
    (tmp_path / "drm.m4p").write_bytes(b"")  # excluded — can't be decoded

    lib = FolderLibrary(tmp_path)
    assert lib.playlist_names() == [tmp_path.name]

    songs = lib.songs_in_playlist(tmp_path.name)
    assert [s.title for s in songs] == ["zebra", "apple"]  # by mtime, not A–Z
    assert all(s.location is not None for s in songs)


def test_unknown_playlist_is_empty(tmp_path):
    assert FolderLibrary(tmp_path).songs_in_playlist("other") == []
