"""Entry point: `python -m songstem` and the `songstem` gui-script."""

from __future__ import annotations

import sys


def main() -> int:
    from songstem.app import run

    return run()


if __name__ == "__main__":
    sys.exit(main())
