"""Entry point: ``python -m dotviewer`` or ``dotviewer`` script."""

from __future__ import annotations

import sys

from .app import DotApp


def main() -> None:
    sys.exit(DotApp().run())


if __name__ == "__main__":
    main()
