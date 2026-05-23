"""PvlDotWindow — viewer window backed by QWebEngineView for browser-grade rendering."""

from __future__ import annotations

import os
import re
import sys
from collections.abc import Callable
from functools import cache
from importlib.resources import files
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
    overflow: hidden; background: __BG_COLOR__;
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
  #logo {
    position: fixed; top: 14px; right: 16px;
    width: 420px; height: auto;
    pointer-events: none;       /* let pan-drags through */
    opacity: 0.9;
    z-index: 10;
  }
  #logo svg { width: 100%; height: auto; display: block; }
  /* Invert/dark mode: GPU-applied lightness inversion with hue preserved.
     `invert(1)` flips R/G/B (which also flips hue by 180°).
     `hue-rotate(180deg)` rotates the hue back to where it was.
     Net effect: lightness inverted, hue + saturation preserved
     (≈ HSL/HSI `L = 1 − L` with hue and saturation untouched).

     The filter is applied to the whole body so the body's background
     color goes through the SAME transformation as the SVG's background
     polygon — they stay matched by construction. */
  body.dark { filter: invert(1) hue-rotate(180deg); }
  .placeholder {
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    height: 100vh; padding: 0 24px; gap: 28px;
    font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", sans-serif;
    text-align: center; color: #888;
  }
  .placeholder .big { font-size: 16px; }
  .placeholder .hints {
    display: flex; flex-direction: column;
    align-items: center; gap: 8px;
    font-size: 13px;
  }
  .placeholder .hints kbd { margin-right: 6px; }
  .placeholder kbd {
    display: inline-block; padding: 2px 8px;
    border: 1px solid #bbb; border-radius: 4px;
    background: #f5f5f5; color: #333;
    font-family: ui-monospace, Menlo, monospace; font-size: 12px;
    white-space: nowrap;
  }
  /* When no graph is loaded, the viewport is "inert": no grab cursor. */
  #viewport:not(:has(svg)) { cursor: default; }
</style>
</head>
<body class="__BODY_CLASS__">
<div id="viewport"><div id="content">__CONTENT__</div></div>
<div id="logo">__LOGO_SVG__</div>
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

  function hasGraph() { return content.querySelector('svg') !== null; }

  viewport.addEventListener('wheel', (e) => {
    if (!hasGraph()) return;     // no zoom on the placeholder
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
    if (e.button !== 0 || !hasGraph()) return;   // no pan on the placeholder
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

  // Expose so Python (via runJavaScript) can trigger ⌘0 fit-to-window.
  window.fitToViewport = fitToViewport;

  // Initial fit. setTimeout 0 lets the SVG layout settle first.
  setTimeout(fitToViewport, 0);
  window.addEventListener('load', fitToViewport);
})();
</script>
</body>
</html>
"""


DEFAULT_BG_COLOR = "#ffffff"


@cache
def _logo_svg() -> str:
    """Load the bundled ParkviewLab logo SVG as a string (cached)."""
    return (
        files("pvl_dotview").joinpath("assets/parkview_lab_logo.svg").read_text()
    )


def _placeholder_html() -> str:
    """Build the empty-window placeholder with platform-correct shortcut hints."""
    cmd = "⌘" if sys.platform == "darwin" else "Ctrl+"
    return (
        '<div class="placeholder">'
        '<div class="big">Drop a .dot file here</div>'
        '<div class="hints">'
        f"<div><kbd>{cmd}N</kbd>new window</div>"
        f"<div><kbd>{cmd}0</kbd>fit to window</div>"
        f"<div><kbd>{cmd}I</kbd>invert colors</div>"
        "</div>"
        "</div>"
    )

# Graphviz always emits the graph background as the first <polygon> with
# stroke="none" (subsequent polygons are nodes/arrowheads and have a stroke).
_BG_POLYGON_RE = re.compile(r'<polygon\s+fill="([^"]+)"\s+stroke="none"\s+points=')


def _strip_svg_prologue(svg_text: str) -> str:
    """Drop <?xml?> / <!DOCTYPE> for clean HTML embedding."""
    idx = svg_text.find("<svg")
    return svg_text[idx:] if idx >= 0 else svg_text


def _extract_svg_bg_color(svg_text: str) -> str:
    """Return the graph background fill (CSS-compatible) or default white."""
    m = _BG_POLYGON_RE.search(svg_text)
    return m.group(1) if m else DEFAULT_BG_COLOR


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

        self._build_actions()
        self._install_menus()
        self._show_placeholder()

    def _build_actions(self) -> None:
        """Create the QActions used by both keyboard shortcuts and the menu bar.

        Saving them as attrs lets the menu bar reuse the same instances —
        Qt then automatically displays each action's shortcut next to its
        menu item.
        """
        self._new_action = QAction("New Window", self)
        self._new_action.setShortcut(QKeySequence.StandardKey.New)
        self._new_action.triggered.connect(self._app.new_window)
        self.addAction(self._new_action)

        self._invert_action = QAction("Invert Colors", self)
        self._invert_action.setShortcut(QKeySequence("Ctrl+I"))  # ⌘I on macOS
        self._invert_action.setCheckable(True)
        self._invert_action.triggered.connect(self._set_dark)
        self.addAction(self._invert_action)

        self._fit_action = QAction("Fit to Window", self)
        self._fit_action.setShortcut(QKeySequence("Ctrl+0"))  # ⌘0 on macOS
        self._fit_action.triggered.connect(self._fit_to_window)
        self.addAction(self._fit_action)

        self._quit_action = QAction("Quit", self)
        self._quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        self._quit_action.setMenuRole(QAction.MenuRole.QuitRole)  # → macOS App menu
        self._quit_action.triggered.connect(self._app._qapp.quit)
        self.addAction(self._quit_action)

        self._about_action = QAction("About pvl-dotview", self)
        self._about_action.setMenuRole(QAction.MenuRole.AboutRole)  # → macOS App menu
        self._about_action.triggered.connect(self._show_about)
        self.addAction(self._about_action)

    def _install_menus(self) -> None:
        """Build the menu bar.

        On macOS this attaches to the native top-of-screen menu bar; on
        Linux/Windows it renders as an in-window strip below the title bar.
        Quit and About carry MenuRole hints so macOS pulls them into the
        Application (bold app-name) menu instead of File / Help.
        """
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")
        file_menu.addAction(self._new_action)
        file_menu.addSeparator()
        file_menu.addAction(self._quit_action)

        view_menu = menubar.addMenu("View")
        view_menu.addAction(self._fit_action)
        view_menu.addAction(self._invert_action)

        help_menu = menubar.addMenu("Help")
        help_menu.addAction(self._about_action)

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "About pvl-dotview",
            "<h3>pvl-dotview</h3>"
            "<p>Interactive Graphviz DOT file viewer.</p>"
            "<p>Drag a <code>.dot</code> file onto the window to render it. "
            "Pan, zoom, invert colors, open multiple windows.</p>"
            "<p>MIT-licensed. © GaryCoding, Claude Code.</p>"
            '<p><a href="https://github.com/ParkviewLab/pvl-dotview">'
            "github.com/ParkviewLab/pvl-dotview</a></p>",
        )

    def _build_html(self, content: str, bg_color: str = DEFAULT_BG_COLOR) -> str:
        body_class = "dark" if self._dark else ""
        return (
            HTML_TEMPLATE.replace("__BODY_CLASS__", body_class)
            .replace("__BG_COLOR__", bg_color)
            .replace("__LOGO_SVG__", _logo_svg())
            .replace("__CONTENT__", content)
        )

    def _set_dark(self, on: bool) -> None:
        """Apply / clear dark mode. Receives the new state from the QAction."""
        self._dark = on
        page = self._view.page()
        # Apply via JS so we don't rebuild the page (preserves zoom/pan).
        # The class is also baked in by _build_html on the next full load.
        if on:
            page.runJavaScript("document.body.classList.add('dark')")
        else:
            page.runJavaScript("document.body.classList.remove('dark')")

    def _fit_to_window(self) -> None:
        # JS function is exposed as window.fitToViewport. Guarded so a stray
        # ⌘0 over the placeholder page doesn't error if it's not yet bound.
        self._view.page().runJavaScript(
            "if (window.fitToViewport) window.fitToViewport()"
        )

    def _show_placeholder(self) -> None:
        self._view.setHtml(self._build_html(_placeholder_html()))

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

        bg_color = _extract_svg_bg_color(svg_body)
        self._view.setHtml(self._build_html(svg_body, bg_color))
        self.setWindowTitle(f"pvl-dotview — {filename}")

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        self._app.remove_window(self)
        super().closeEvent(event)
