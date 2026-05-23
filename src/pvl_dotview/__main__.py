"""Entry point: ``python -m pvl_dotview`` or ``pvl-dotview`` script."""

from __future__ import annotations

import sys

from .app import DotApp


def main() -> None:
    sys.exit(DotApp().run())


if __name__ == "__main__":
    main()
