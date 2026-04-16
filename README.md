# Drawer

[![Build](https://github.com/varg90/drawer/actions/workflows/build.yml/badge.svg)](https://github.com/varg90/drawer/actions/workflows/build.yml)
[![Release](https://img.shields.io/github/v/release/varg90/drawer?include_prereleases&sort=semver)](https://github.com/varg90/drawer/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS-lightgrey)](#installation)

A reference image viewer with timers for figure drawing, gesture practice, and art studies. Built with Python and PyQt6.

## Features

- **Timed sessions** — Quick mode (same timer per image) or Class mode (auto-distributed tiers for warmups → long poses)
- **Session time limit** with progress bar and alert when time runs out
- **Extend current image** on the fly without breaking the session rhythm
- **Auto-pause** when a chosen app loses focus (e.g. pause when your drawing app isn't in front)
- **Frameless viewer** — always-on-top toggle, drag to move (RMB), resize from edges, aspect-aware minimum size
- **Image tools** — black & white, rule-of-thirds grid, horizontal/vertical flip
- **File manager** — drag & drop, multi-select, shuffle, manual reorder, pin, redistribute across tiers; detachable and resizable
- **Custom theme** — light/dark mode and accent color picker

## Installation

Prebuilt binaries are published on the [Releases](https://github.com/varg90/drawer/releases) page.

### Windows

- **Installer** — `Drawer-<version>-setup.exe` (recommended). Adds Start menu and optional desktop shortcuts.
- **Portable** — `Drawer-<version>.exe`. Single file, no install.

### macOS

- `Drawer-<version>.dmg` — drag `Drawer.app` into `/Applications`.
- On first launch macOS may block the app: right-click → **Open** → **Open** to bypass Gatekeeper (the app is not code-signed).

### From source

Requires **Python 3.10+**.

```bash
git clone https://github.com/varg90/drawer.git
cd drawer
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
python main.py
```

## Usage

### Main window

| Control | Action |
|---|---|
| Pencil | Start session |
| Image icon | Open file manager |
| Sun / Moon | Toggle theme |
| Palette | Pick accent color |
| LMB on session time | Forward |
| RMB on session time | Back |

### File manager

| Control | Action |
|---|---|
| Drag & drop | Add files |
| `+` / `-` or `Ctrl` + scroll | Resize preview |
| `Shift` / `Ctrl` + click | Multi-select |
| `Delete` | Remove selected |
| Eraser | Clear list |
| Shuffle toggle | Lock / unlock manual reorder |
| RMB on file | Redistribute or pin |

### Viewer hotkeys

| Key | Action |
|---|---|
| `Space` | Pause / resume |
| `←` / `→` | Previous / next image |
| `+` / `=` | Extend current image timer |
| `P` | Always-on-top toggle |
| `F11` | Fullscreen |
| `Esc` | Exit fullscreen |
| `G` | Black & white |
| `R` | Rule-of-thirds grid |
| `F` | Flip horizontal |
| `V` | Flip vertical |
| `H` | Help overlay |
| RMB + drag | Move window |

## Running tests

```bash
pip install pytest
pytest
```

## Building from source

The [build workflow](.github/workflows/build.yml) produces Windows (installer + portable) and macOS (`.dmg`) artifacts on every push to `main` and attaches them to releases on `v*` tags.

To build locally:

```bash
pip install pyinstaller
pyinstaller Drawer.spec
# Windows installer (requires Inno Setup)
iscc /DAppVersion=0.4.6 installer.iss
```

Outputs land in `dist/`.

## Project structure

```
core/      session logic, timers, models
ui/        PyQt6 widgets and windows
fonts/     bundled Lora and Lexend font files
tests/     pytest unit tests
```

## Contributing

Issues and pull requests are welcome. For larger changes, open an issue first to discuss the direction.

## License

[MIT](LICENSE) — free to use, modify, and share.

## Credits

- Created by valerianashot (GitHub: [@varg90](https://github.com/varg90))
- Fonts: [Lora](https://fonts.google.com/specimen/Lora), [Lexend](https://fonts.google.com/specimen/Lexend)
- Icons via [QtAwesome](https://github.com/spyder-ide/qtawesome)

## Contact

valerianashot@gmail.com
