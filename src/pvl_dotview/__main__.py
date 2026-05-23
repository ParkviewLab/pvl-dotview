"""Entry point: ``python -m pvl_dotview`` or ``pvl-dotview`` script."""

from __future__ import annotations

import sys

from .app import PvlDotApp


def main() -> None:
    sys.exit(PvlDotApp().run())


if __name__ == "__main__":
    main()
