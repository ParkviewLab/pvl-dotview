# Py-DOT-Views

Interactive Graphviz DOT file viewer. Drop a `.dot` file onto a blank window
and the graph is rendered as crisp, pannable, zoomable vector graphics. Open
additional windows with **⌘N** (macOS) or **Ctrl+N** (Linux/Windows).

## Install

`dotviewer` shells out to the `dot` binary at runtime, so Graphviz must be
installed system-wide before running.

### macOS

```bash
brew install graphviz
uv sync
```

### Linux (Debian/Ubuntu)

```bash
sudo apt install graphviz
uv sync
```

## Run

```bash
uv run dotviewer
```

## License

This project is released under the [MIT License](LICENSE).

Third-party components and their licenses are listed in [NOTICE](NOTICE):

- **PySide6** (LGPL-3.0) — used as a dynamically-linked dependency
- **pygraphviz** (BSD-3-Clause)
- **Graphviz** (EPL-1.0, system dependency)
