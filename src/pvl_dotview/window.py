"""PvlDotWindow — viewer window backed by QWebEngineView for browser-grade rendering."""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import TYPE_CHECKING, cast

from PySide6.QtCore import QChildEvent, QEvent, QObject
from PySide6.QtGui import (
    QAction,
    QCloseEvent,
    QDragEnterEvent,
    QDragMoveEvent,
    QDropEvent,
    QKeySequence,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QMainWindow, QMessageBox, QWidget

from .renderer import GraphvizNotFoundError, GraphvizRenderError, render_dot_to_svg

if TYPE_CHECKING:
    from .app import PvlDotApp


HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  html, body {
    margin: 0; padding: 0; width: 100%; height: 100%;
    overflow: hidden; background: #ffffff;
    -webkit-user-select: none; user-select: none;
  }
  #viewport {
    position: fixed; inset: 0; overflow: hidden;
    cursor: grab;
  }
  #viewport.panning { cursor: grabbing; }
  #content {
    position: absolute; top: 0; left: 0;
    transform-origin: 0 0;
    will-change: transform;
  }
  #content svg { display: block; }
  /* Invert/dark mode: GPU-applied lightness inversion with hue preserved.
     `invert(1)` flips R/G/B (which also flips hue by 180°).
     `hue-rotate(180deg)` rotates the hue back to where it was.
     Net effect: lightness inverted, hue + saturation preserved
     (≈ HSL/HSI `L = 1 − L` with hue and saturation untouched). */
  body.dark { background: #000000; }
  body.dark #content { filter: invert(1) hue-rotate(180deg); }
  .placeholder {
    display: flex; align-items: center; justify-content: center;
    height: 100vh; padding: 0 24px;
    font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", sans-serif;
    text-align: center; color: #888; font-size: 16px;
  }
</style>
</head>
<body class="__BODY_CLASS__">
<div id="viewport"><div id="content">__CONTENT__</div></div>
<script>
(function(){
  const viewport = document.getElementById('viewport');
  const content = document.getElementById('content');

  let scale = 1, tx = 0, ty = 0;
  const ZOOM_BASE = 1.0015;
  const ZOOM_MIN = 0.05;
  const ZOOM_MAX = 50;

  function applyTransform() {
    content.style.transform = `translate(${tx}px, ${ty}px) scale(${scale})`;
  }

  function fitToViewport() {
    const svg = content.querySelector('svg');
    if (!svg) {
      tx = 0; ty = 0; scale = 1;
      applyTransform();
      return;
    }
    let svgW = 0, svgH = 0;
    if (svg.viewBox && svg.viewBox.baseVal && svg.viewBox.baseVal.width) {
      svgW = svg.viewBox.baseVal.width;
      svgH = svg.viewBox.baseVal.height;
    } else if (svg.width && svg.width.baseVal) {
      svgW = svg.width.baseVal.value;
      svgH = svg.height.baseVal.value;
    }
    if (!svgW || !svgH) return;
    svg.style.width = svgW + 'px';
    svg.style.height = svgH + 'px';
    const vw = viewport.clientWidth, vh = viewport.clientHeight;
    scale = Math.min(vw / svgW, vh / svgH) * 0.95;
    tx = (vw - svgW * scale) / 2;
    ty = (vh - svgH * scale) / 2;
    applyTransform();
  }

  viewport.addEventListener('wheel', (e) => {
    e.preventDefault();
    const delta = e.deltaY;
    let factor = Math.pow(ZOOM_BASE, -delta);
    let newScale = scale * factor;
    if (newScale < ZOOM_MIN) { factor = ZOOM_MIN / scale; newScale = ZOOM_MIN; }
    if (newScale > ZOOM_MAX) { factor = ZOOM_MAX / scale; newScale = ZOOM_MAX; }
    const rect = viewport.getBoundingClientRect();
    const cx = e.clientX - rect.left;
    const cy = e.clientY - rect.top;
    tx = cx - (cx - tx) * factor;
    ty = cy - (cy - ty) * factor;
    scale = newScale;
    applyTransform();
  }, { passive: false });

  let panning = false, lastX = 0, lastY = 0;
  viewport.addEventListener('mousedown', (e) => {
    if (e.button !== 0) return;
    panning = true;
    lastX = e.clientX; lastY = e.clientY;
    viewport.classList.add('panning');
    e.preventDefault();
  });
  document.addEventListener('mousemove', (e) => {
    if (!panning) return;
    tx += e.clientX - lastX;
    ty += e.clientY - lastY;
    lastX = e.clientX; lastY = e.clientY;
    applyTransform();
  });
  document.addEventListener('mouseup', () => {
    if (!panning) return;
    panning = false;
    viewport.classList.remove('panning');
  });

  // Initial fit. setTimeout 0 lets the SVG layout settle first.
  setTimeout(fitToViewport, 0);
  window.addEventListener('load', fitToViewport);
})();
</script>
</body>
</html>
"""


PLACEHOLDER_BODY = '<div class="placeholder">Drop a .dot file here</div>'


def _strip_svg_prologue(svg_text: str) -> str:
    """Drop <?xml?> / <!DOCTYPE> for clean HTML embedding."""
    idx = svg_text.find("<svg")
    return svg_text[idx:] if idx >= 0 else svg_text


class _DropFilter(QObject):
    """Intercept drag-drop events on the webview and any of its inner widgets.

    QWebEngineView has internal Chromium widgets that consume drag-drop events;
    a filter installed on the view and each of its children catches drops
    regardless of which inner widget receives the OS event first.
    """

    def __init__(self, on_file_dropped: Callable[[str], None]) -> None:
        super().__init__()
        self._on_file_dropped = on_file_dropped

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802
        t = event.type()
        if t == QEvent.Type.DragEnter:
            ev = cast(QDragEnterEvent, event)
            if ev.mimeData().hasUrls():
                ev.acceptProposedAction()
                return True
        elif t == QEvent.Type.DragMove:
            mv = cast(QDragMoveEvent, event)
            if mv.mimeData().hasUrls():
                mv.acceptProposedAction()
                return True
        elif t == QEvent.Type.Drop:
            drop = cast(QDropEvent, event)
            for url in drop.mimeData().urls():
                path = url.toLocalFile()
                if path:
                    self._on_file_dropped(path)
                    drop.acceptProposedAction()
                    return True
        elif t == QEvent.Type.ChildAdded:
            # A new internal widget was just attached — make sure it accepts
            # drops and routes through this filter too.
            child_ev = cast(QChildEvent, event)
            child = child_ev.child()
            if isinstance(child, QWidget):
                child.setAcceptDrops(True)
                child.installEventFilter(self)
        return super().eventFilter(obj, event)


class PvlDotWindow(QMainWindow):
    def __init__(self, app: PvlDotApp) -> None:
        super().__init__()
        self._app = app
        self._dark = False
        self.setWindowTitle("pvl-dotview")
        self.resize(900, 700)

        self._view = QWebEngineView(self)
        self.setCentralWidget(self._view)

        self._drop_filter = _DropFilter(on_file_dropped=self._load)
        self.setAcceptDrops(True)
        self.installEventFilter(self._drop_filter)
        self._view.setAcceptDrops(True)
        self._view.installEventFilter(self._drop_filter)
        for child in self._view.findChildren(QWidget):
            child.setAcceptDrops(True)
            child.installEventFilter(self._drop_filter)

        self._show_placeholder()
        self._install_shortcuts()

    def _install_shortcuts(self) -> None:
        new_action = QAction("New Window", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self._app.new_window)
        self.addAction(new_action)

        invert_action = QAction("Invert Colors", self)
        invert_action.setShortcut(QKeySequence("Ctrl+I"))  # auto-maps to ⌘I on macOS
        invert_action.triggered.connect(self._toggle_dark)
        self.addAction(invert_action)

    def _build_html(self, content: str) -> str:
        body_class = "dark" if self._dark else ""
        return HTML_TEMPLATE.replace("__BODY_CLASS__", body_class).replace(
            "__CONTENT__", content
        )

    def _toggle_dark(self) -> None:
        self._dark = not self._dark
        page = self._view.page()
        # Apply via JS so we don't rebuild the page (preserves zoom/pan).
        # The class is also baked in by _build_html on the next full load.
        if self._dark:
            page.runJavaScript("document.body.classList.add('dark')")
        else:
            page.runJavaScript("document.body.classList.remove('dark')")

    def _show_placeholder(self) -> None:
        self._view.setHtml(self._build_html(PLACEHOLDER_BODY))

    def _load(self, path: str) -> None:
        filename = os.path.basename(path)
        try:
            with open(path) as f:
                dot_source = f.read()
            svg_body = _strip_svg_prologue(render_dot_to_svg(dot_source).decode("utf-8"))
        except GraphvizNotFoundError as exc:
            QMessageBox.warning(self, "Graphviz not installed", str(exc))
            return
        except GraphvizRenderError as exc:
            QMessageBox.warning(self, "Cannot render DOT file", f"{filename}\n\n{exc}")
            return
        except OSError as exc:
            QMessageBox.warning(self, "Cannot read file", f"{filename}\n\n{exc}")
            return
        except Exception as exc:
            # Catch-all so unexpected failures (UnicodeDecodeError, MemoryError,
            # anything from the subprocess layer we didn't anticipate) show a
            # dialog and the app keeps running instead of crashing.
            QMessageBox.warning(
                self,
                "Unexpected error loading file",
                f"{filename}\n\n{type(exc).__name__}: {exc}",
            )
            return

        self._view.setHtml(self._build_html(svg_body))
        self.setWindowTitle(f"pvl-dotview — {filename}")

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        self._app.remove_window(self)
        super().closeEvent(event)
