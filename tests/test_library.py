from songstem.itunes.library import FakeLibrary
from songstem.models import Song


def test_fake_library_lists_playlists_and_songs():
    lib = FakeLibrary({"Practice": [Song(title="A", artist="X"), Song(title="B", artist="Y")]})
    assert lib.playlist_names() == ["Practice"]
    assert [s.title for s in lib.songs_in_playlist("Practice")] == ["A", "B"]


def test_unknown_playlist_is_empty():
    assert FakeLibrary().songs_in_playlist("nope") == []
