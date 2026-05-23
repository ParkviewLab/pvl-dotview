# pvl-dotview

Interactive Graphviz DOT file viewer. Drop a `.dot` file onto a blank window
and the graph is rendered as crisp, pannable, zoomable vector graphics
(via embedded Chromium / Qt WebEngine for browser-grade SVG fidelity). Open
additional windows with **⌘N** (macOS) or **Ctrl+N** (Linux/Windows).

## Install

`pvl-dotview` shells out to the `dot` binary at runtime, so Graphviz must be
installed system-wide before running.

### As a tool (recommended for end users)

```bash
# macOS
brew install graphviz
uv tool install pvl-dotview

# Debian/Ubuntu
sudo apt install graphviz
uv tool install pvl-dotview
```

Then run `pvl-dotview` from any terminal.

### From a checkout (for development)

```bash
brew install graphviz   # or: apt install graphviz
uv sync
uv run pvl-dotview
```

## License

This project is released under the [MIT License](LICENSE).

Third-party components and their licenses are listed in [NOTICE](NOTICE):

- **PySide6** (LGPL-3.0) — used as a dynamically-linked dependency
- **Graphviz** (EPL-1.0, system dependency, invoked via the `dot` binary)
