"""Render a DOT source string to SVG bytes via the system graphviz layout."""

from __future__ import annotations

import pygraphviz


def render_dot_to_svg(dot_source: str) -> bytes:
    """Lay out the DOT source and emit SVG bytes."""
    g = pygraphviz.AGraph(string=dot_source)
    g.layout(prog="dot")
    return g.draw(format="svg")
