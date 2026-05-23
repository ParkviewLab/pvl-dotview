# Py-DOT-Views

Interactive Graphviz DOT file viewer. Drop a `.dot` file onto a blank window
and the graph is rendered as crisp, pannable, zoomable vector graphics. Open
additional windows with **⌘N** (macOS) or **Ctrl+N** (Linux/Windows).

## Install

### macOS

```bash
brew install graphviz
uv sync \
  --config-settings="pygraphviz=--build-option=build_ext" \
  --config-settings="pygraphviz=--build-option=-I$(brew --prefix graphviz)/include/" \
  --config-settings="pygraphviz=--build-option=-L$(brew --prefix graphviz)/lib/"
```

### Linux (Debian/Ubuntu)

```bash
sudo apt install graphviz graphviz-dev
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
