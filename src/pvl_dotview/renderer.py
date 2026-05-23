"""Render a DOT source string to SVG bytes via the graphviz `dot` binary."""

from __future__ import annotations

import shutil
import subprocess


class GraphvizNotFoundError(RuntimeError):
    """The `dot` binary is not on PATH."""


class GraphvizRenderError(RuntimeError):
    """`dot` exited non-zero (DOT syntax error or other failure)."""


def render_dot_to_svg(dot_source: str) -> bytes:
    """Invoke `dot -Tsvg` on the DOT source and return the SVG bytes."""
    if not shutil.which("dot"):
        raise GraphvizNotFoundError(
            "Graphviz `dot` binary not found on PATH. "
            "Install with `brew install graphviz` (macOS) or "
            "`apt install graphviz` (Linux)."
        )
    try:
        result = subprocess.run(
            ["dot", "-Tsvg"],
            input=dot_source.encode("utf-8"),
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", errors="replace").strip()
        raise GraphvizRenderError(stderr or f"dot exited {exc.returncode}") from exc
    return result.stdout
