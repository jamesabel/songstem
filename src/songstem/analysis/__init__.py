"""Audio analysis and player cheat-sheet generation for isolated stems.

The pure, backend-agnostic core (models, key/note/lyric logic, markdown builder) imports
nothing heavy. librosa and `syncedlyrics` are imported locally inside the concrete adapters in
`analyzer` and `lyrics`, which sit behind ABCs with in-memory fakes — so the bulk of this
package is testable without the ML/network stack.
"""

from songstem.analysis.models import (
    AudioAnalysis,
    CheatSheet,
    KeyEstimate,
    LyricLine,
    NoteEvent,
)
from songstem.analysis.session import generate_cheat_sheet

__all__ = [
    "AudioAnalysis",
    "CheatSheet",
    "KeyEstimate",
    "LyricLine",
    "NoteEvent",
    "generate_cheat_sheet",
]
