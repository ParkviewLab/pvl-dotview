"""DotApp — application singleton owning the QApplication and window registry."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .window import DotWindow


class DotApp:
    def __init__(self) -> None:
        self._qapp = QApplication.instance() or QApplication(sys.argv)
        self._windows: list[DotWindow] = []
        self.new_window()

    def new_window(self) -> DotWindow:
        window = DotWindow(self)
        window.show()
        self._windows.append(window)
        return window

    def remove_window(self, window: DotWindow) -> None:
        if window in self._windows:
            self._windows.remove(window)

    def run(self) -> int:
        return self._qapp.exec()
