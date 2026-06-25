"""Render src/songstem/resources/icon.svg to songstem.png and a multi-size songstem.ico.

Run after editing icon.svg:  python scripts/generate_icon.py
Uses Qt (QtSvg) to rasterize; assembles the .ico container by hand so no extra deps are
needed (each .ico entry is a PNG payload, which Windows Vista+ supports).
"""

from __future__ import annotations

import os
import struct
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QBuffer, QByteArray, Qt  # noqa: E402
from PySide6.QtGui import QImage, QPainter  # noqa: E402
from PySide6.QtSvg import QSvgRenderer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

RES = Path(__file__).resolve().parents[1] / "src" / "songstem" / "resources"
ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]


def _render_png(renderer: QSvgRenderer, size: int) -> bytes:
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter()
    painter.begin(image)
    renderer.render(painter)
    painter.end()
    data = QByteArray()  # keep a reference; a temporary here gets GC'd mid-write and crashes
    buffer = QBuffer(data)
    buffer.open(QBuffer.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    buffer.close()
    return bytes(data)


def _build_ico(pngs: dict[int, bytes]) -> bytes:
    count = len(pngs)
    header = struct.pack("<HHH", 0, 1, count)  # reserved, type=icon, count
    entries = b""
    payload = b""
    offset = 6 + count * 16
    for size, png in sorted(pngs.items()):
        dim = 0 if size >= 256 else size  # 0 means 256 in the ICO spec
        entries += struct.pack(
            "<BBBBHHII", dim, dim, 0, 0, 1, 32, len(png), offset
        )
        payload += png
        offset += len(png)
    return header + entries + payload


def main() -> None:
    QApplication([])  # QImage/QPainter need a QGuiApplication
    renderer = QSvgRenderer(str(RES / "icon.svg"))
    pngs = {size: _render_png(renderer, size) for size in ICO_SIZES}
    (RES / "songstem.ico").write_bytes(_build_ico(pngs))
    (RES / "songstem.png").write_bytes(pngs[256])
    print(f"wrote {RES/'songstem.ico'} and {RES/'songstem.png'}")


if __name__ == "__main__":
    main()
