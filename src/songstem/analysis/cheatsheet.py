"""Render a CheatSheet to compact, one-page Markdown (tuned for US Letter)."""

from __future__ import annotations

from dataclasses import dataclass

from songstem.analysis.models import CheatSheet
from songstem.analysis.notes import most_common_pitch_classes


@dataclass
class PageBudget:
    """Content caps so the sheet fits one US Letter page at a normal iPad zoom.

    Markdown→page-size isn't deterministic, so these are heuristics, not guarantees.
    """

    max_lyric_lines: int = 16
    max_total_lines: int = 50


def _fmt_duration(seconds: float) -> str:
    total = int(round(seconds))
    return f"{total // 60}:{total % 60:02d}"


def _sample_evenly(items: list, limit: int) -> list:
    """At most `limit` items, evenly spaced across `items` (keeps first and last)."""
    if len(items) <= limit:
        return items
    step = (len(items) - 1) / (limit - 1)
    return [items[round(i * step)] for i in range(limit)]


def build_markdown(sheet: CheatSheet, budget: PageBudget | None = None) -> str:
    budget = budget or PageBudget()
    a = sheet.analysis
    lines: list[str] = [
        f"# {sheet.title} — {sheet.artist}",
        "",
        f"**Key** {a.key.name} · **Tempo** {round(a.tempo_bpm)} BPM · "
        f"**Stem** {sheet.stem.capitalize()} · **Length** {_fmt_duration(a.duration)}",
        "",
        f"**Scale:** {' '.join(a.scale_notes)}",
    ]

    if a.notes_reliable:
        top = most_common_pitch_classes(a.note_events)
        if top:
            lines.append(f"**Most-used notes:** {' · '.join(top)}")
        lines += _lyrics_with_notes_block(sheet, budget)
    else:
        lines += [
            "",
            "> Per-note detection isn't reliable for polyphonic stems (guitar/piano/other); "
            "key, tempo, and scale are estimated from the overall harmony.",
        ]
        lines += _lyrics_text_block(sheet, budget)

    return "\n".join(lines).rstrip() + "\n"


def _lyrics_with_notes_block(sheet: CheatSheet, budget: PageBudget) -> list[str]:
    if not sheet.lyric_notes:
        return []
    rows = _sample_evenly(sheet.lyric_notes, budget.max_lyric_lines)
    out = ["", "### Lyrics & notes", "", "| Lyric | Notes |", "|-------|-------|"]
    for line, note in rows:
        out.append(f"| {_escape(line.text)} | {note or ''} |")
    return out


def _lyrics_text_block(sheet: CheatSheet, budget: PageBudget) -> list[str]:
    if not sheet.lyric_notes:
        return []
    rows = _sample_evenly([ln for ln, _ in sheet.lyric_notes], budget.max_lyric_lines)
    out = ["", "### Lyrics", ""]
    out += [f"- {_escape(line.text)}" for line in rows]
    return out


def _escape(text: str) -> str:
    return text.replace("|", "\\|").strip()
