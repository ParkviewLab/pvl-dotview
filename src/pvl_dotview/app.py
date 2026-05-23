"""PvlDotApp — application singleton owning the QApplication and window registry."""

from __future__ import annotations

import contextlib
import sys
import traceback
from types import TracebackType

from PySide6.QtWidgets import QApplication, QMessageBox

from .window import PvlDotWindow


class PvlDotApp:
    def __init__(self) -> None:
        self._qapp = QApplication.instance() or QApplication(sys.argv)
        self._windows: list[PvlDotWindow] = []
        sys.excepthook = self._on_uncaught_exception
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

    def _on_uncaught_exception(
        self,
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_tb: TracebackType | None,
    ) -> None:
        # Always print to stderr so the trace lands in the terminal too.
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        # Don't pop a dialog for KeyboardInterrupt — let it propagate cleanly.
        if issubclass(exc_type, KeyboardInterrupt):
            return
        tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        parent = self._windows[0] if self._windows else None
        # If the dialog itself fails, we've already printed to stderr.
        with contextlib.suppress(Exception):
            QMessageBox.critical(
                parent,
                "Unexpected error",
                f"{exc_type.__name__}: {exc_value}\n\n{tb}",
            )
