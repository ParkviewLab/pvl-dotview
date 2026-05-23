"""PvlDotApp — application singleton owning the QApplication and window registry."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .window import PvlDotWindow


class PvlDotApp:
    def __init__(self) -> None:
        self._qapp = QApplication.instance() or QApplication(sys.argv)
        self._windows: list[PvlDotWindow] = []
        self.new_window()

    def new_window(self) -> PvlDotWindow:
        window = PvlDotWindow(self)
        window.show()
        self._windows.append(window)
        return window

    def remove_window(self, window: PvlDotWindow) -> None:
        if window in self._windows:
            self._windows.remove(window)

    def run(self) -> int:
        return self._qapp.exec()
