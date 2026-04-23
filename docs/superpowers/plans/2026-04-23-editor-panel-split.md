# Editor Panel Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split `ui/editor_panel.py` (1787 lines) into a `ui/editor_panel/` package with focused modules. Zero behavior change.

**Architecture:** Mechanical relocation of module-level helpers and small widget classes out of the monolith into sibling modules inside a new `ui/editor_panel/` package. `EditorPanel` class itself stays intact in `panel.py`. An `__init__.py` re-exports every public and test-imported name so callers need no changes.

**Tech Stack:** Python 3.14, PyQt6, pytest.

**Spec:** `docs/superpowers/specs/2026-04-23-editor-panel-split-design.md`

**Branch:** `chore/split-editor-panel` (already created).

---

## Pre-flight

Before starting any task:

- [ ] Confirm branch: `git branch --show-current` → `chore/split-editor-panel`
- [ ] Confirm tests green on baseline: `python -m pytest tests/ -q` → all pass
- [ ] Confirm app launches: `python main.py` → editor opens, works. Close.

If any of the above fails, STOP. Do not start extraction. Investigate first.

---

## Task 1: Create package skeleton

Rename `ui/editor_panel.py` → `ui/editor_panel/__init__.py` so git tracks the move and blame stays intact. No content change yet. After this task everything still works exactly as before — the file has just moved.

**Files:**
- Rename: `ui/editor_panel.py` → `ui/editor_panel/__init__.py`

- [ ] **Step 1: Verify current tests pass**

Run: `python -m pytest tests/ -q`
Expected: all green.

- [ ] **Step 2: Create package dir and move file with git mv**

```bash
mkdir ui/editor_panel
git mv ui/editor_panel.py ui/editor_panel/__init__.py
```

- [ ] **Step 3: Verify tests still pass**

Run: `python -m pytest tests/ -q`
Expected: all green. (Package import resolves the same symbols.)

- [ ] **Step 4: Verify import smoke test**

Run:
```bash
python -c "from ui.editor_panel import EditorPanel, _sort_group_items, _compute_insertion_index, _filter_selection_by_zone, _apply_tile_drop, TILE_DRAG_MIME, ClickableLabel, PixmapLoader, _PinPlaceholderRow, _PinPlaceholderTile; print('OK')"
```
Expected: `OK`.

- [ ] **Step 5: Verify app launches**

Run: `python main.py`
Expected: editor opens, can switch list/grid. Close app.

- [ ] **Step 6: Commit**

```bash
git add ui/editor_panel/__init__.py
git commit -m "refactor: convert ui/editor_panel.py to package

git mv preserves blame. No logic change yet — subsequent commits
extract helpers and widget classes into sibling modules."
```

---

## Task 2: Extract `sort.py`

Move `_sort_group_items` into its own module. Add re-export. Smallest extraction first; validates the pattern the later tasks follow.

**Files:**
- Create: `ui/editor_panel/sort.py`
- Modify: `ui/editor_panel/__init__.py` (remove `_sort_group_items` body, add re-export)

- [ ] **Step 1: Create `ui/editor_panel/sort.py` with the function**

Write `ui/editor_panel/sort.py`:

```python
# ui/editor_panel/sort.py
"""Group-tier sort helper."""


def _sort_group_items(items, pinned_first=True):
    """Sort items within a tier group.

    pinned_first=True: pinned images at the top of the group (quick mode).
    pinned_first=False: list order preserved, pin ignored (class mode).
    """
    if not pinned_first:
        return list(items)
    pinned = [i for i in items if getattr(i[1], "pinned", False)]
    unpinned = [i for i in items if not getattr(i[1], "pinned", False)]
    return pinned + unpinned
```

- [ ] **Step 2: Remove the original `_sort_group_items` definition from `__init__.py`**

In `ui/editor_panel/__init__.py`, delete lines that correspond to the `_sort_group_items` function (the `def _sort_group_items(...)` block — roughly 11 lines starting with `def _sort_group_items(items, pinned_first=True):`).

- [ ] **Step 3: Add re-export at the top of `__init__.py` (below existing imports)**

In `ui/editor_panel/__init__.py`, add:

```python
from ui.editor_panel.sort import _sort_group_items
```

Place it after the existing `from ui.widgets import make_icon_btn` line (the last of the package-external imports).

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_pinned_sort.py tests/ -q`
Expected: all green.

- [ ] **Step 5: Import smoke**

Run:
```bash
python -c "from ui.editor_panel import _sort_group_items; print(_sort_group_items([], True))"
```
Expected: `[]`

- [ ] **Step 6: App launch check**

Run: `python main.py` → opens, list mode works (sort used in `_ordered_groups`). Close.

- [ ] **Step 7: Commit**

```bash
git add ui/editor_panel/sort.py ui/editor_panel/__init__.py
git commit -m "refactor(editor_panel): extract _sort_group_items to sort.py

Re-exported via __init__.py so existing test imports keep working."
```

---

## Task 3: Extract `flow_layout.py`

Move the two pure flow-positioning helpers into their own module.

**Files:**
- Create: `ui/editor_panel/flow_layout.py`
- Modify: `ui/editor_panel/__init__.py`

- [ ] **Step 1: Create `ui/editor_panel/flow_layout.py`**

Write `ui/editor_panel/flow_layout.py`:

```python
# ui/editor_panel/flow_layout.py
"""Flow-layout geometry helpers for the editor grid view."""


def _flow_position(labels, container_width, sz, gap=1):
    """Position labels in a flow layout. Returns total height."""
    x, y, row_h = 0, 0, 0
    for lbl in labels:
        pix = lbl.pixmap()
        if pix and not pix.isNull():
            w, h = pix.width(), pix.height()
        else:
            w, h = sz, sz
        if x + w > container_width and x > 0:
            x = 0
            y += row_h + gap
            row_h = 0
        lbl.setFixedSize(w, h)
        lbl.move(x, y)
        x += w + gap
        row_h = max(row_h, h)
    return y + row_h if labels else 0


def _flow_position_with_gaps(labels_or_none, container_width, sz, gap=1):
    """Same as _flow_position but accepts None entries which reserve a
    tile-sized empty slot at that position (no widget moved)."""
    x, y, row_h = 0, 0, 0
    for entry in labels_or_none:
        if entry is None:
            w, h = sz, sz
        else:
            pix = entry.pixmap()
            if pix and not pix.isNull():
                w, h = pix.width(), pix.height()
            else:
                w, h = sz, sz
        if x + w > container_width and x > 0:
            x = 0
            y += row_h + gap
            row_h = 0
        if entry is not None:
            entry.setFixedSize(w, h)
            entry.move(x, y)
        x += w + gap
        row_h = max(row_h, h)
    return y + row_h if labels_or_none else 0
```

- [ ] **Step 2: Remove original definitions from `__init__.py`**

Delete the `def _flow_position(...)` and `def _flow_position_with_gaps(...)` function bodies from `ui/editor_panel/__init__.py`.

- [ ] **Step 3: Add re-export to `__init__.py`**

Add:
```python
from ui.editor_panel.flow_layout import _flow_position, _flow_position_with_gaps
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/ -q`
Expected: all green.

- [ ] **Step 5: Import smoke**

Run: `python -c "from ui.editor_panel import _flow_position, _flow_position_with_gaps; print('OK')"`
Expected: `OK`

- [ ] **Step 6: App launch check**

Run: `python main.py` → grid view renders correctly, zoom works, reflow on window resize works. Close.

- [ ] **Step 7: Commit**

```bash
git add ui/editor_panel/flow_layout.py ui/editor_panel/__init__.py
git commit -m "refactor(editor_panel): extract flow layout helpers to flow_layout.py"
```

---

## Task 4: Extract `tile_drag.py`

Move the TILE_DRAG_MIME constant and the four pure drag helpers into their own module.

**Files:**
- Create: `ui/editor_panel/tile_drag.py`
- Modify: `ui/editor_panel/__init__.py`

- [ ] **Step 1: Create `ui/editor_panel/tile_drag.py`**

Write `ui/editor_panel/tile_drag.py`:

```python
# ui/editor_panel/tile_drag.py
"""Pure-Python tile-drag helpers: MIME constant + payload + geometry +
selection-zone filter + reorder."""

import json


# Payload for an internal tile drag: JSON-encoded bytes matching
#   {"indices": [int, ...], "source_is_pinned": bool}
# - indices:          positions in EditorPanel.images of the dragged tiles,
#                     already filtered to the pressed tile's zone.
# - source_is_pinned: zone of the pressed tile (convenience hint for the
#                     drop target; can also be re-derived from images[i].pinned).
TILE_DRAG_MIME = "application/x-drawer-tile-indices"


def _decode_tile_drag_payload(mime_data):
    """Robustly decode a TILE_DRAG_MIME payload.

    Returns a list of source indices (ints) or None if the payload is absent,
    malformed JSON, wrong shape, or contains non-int entries.
    """
    if not mime_data.hasFormat(TILE_DRAG_MIME):
        return None
    try:
        raw = bytes(mime_data.data(TILE_DRAG_MIME)).decode("utf-8")
        payload = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    indices = payload.get("indices")
    if not isinstance(indices, list) or not indices:
        return None
    if not all(isinstance(i, int) for i in indices):
        return None
    return indices


def _compute_insertion_index(cursor_pos, tile_rects):
    """Given cursor position (x, y) in the grid container's coordinate system
    and a list of tile rects (idx, x, y, w, h), return the insertion index
    where a dropped tile would land.

    Algorithm:
    - Find the row whose vertical range (y, y+h) contains cursor_y (clamped to
      the nearest row if cursor is above or below all tiles).
    - Within that row, find the first tile whose horizontal midline is past
      cursor_x. Insertion is before that tile.
    - If cursor is after the last tile in the row, insertion is after the
      last tile of the row (which is the index of the first tile in the next
      row, or len(tile_rects) if this is the last row).
    """
    if not tile_rects:
        return 0

    cx, cy = cursor_pos

    # Group rects by row (rects with the same y).
    rows = {}
    for rect in tile_rects:
        idx, x, y, w, h = rect
        rows.setdefault(y, []).append(rect)
    row_ys = sorted(rows.keys())

    # Pick the row the cursor is in (clamp).
    target_y = row_ys[0]
    for y in row_ys:
        h = rows[y][0][4]
        if y <= cy < y + h:
            target_y = y
            break
        if cy >= y:
            target_y = y

    row = sorted(rows[target_y], key=lambda r: r[1])  # sort by x
    for rect in row:
        idx, x, y, w, h = rect
        midline = x + w / 2
        if cx < midline:
            return idx
    # Cursor is past the last tile in this row — insert after it.
    last_idx = row[-1][0]
    return last_idx + 1


def _filter_selection_by_zone(indices, source_is_pinned, images):
    """Return the subset of `indices` whose images share `source_is_pinned`.

    Used when the user presses on a selected tile to start a multi-select
    drag: only tiles in the pressed tile's zone participate."""
    result = []
    for i in indices:
        if 0 <= i < len(images) and bool(images[i].pinned) == source_is_pinned:
            result.append(i)
    return result


def _apply_tile_drop(images, source_indices, insert_idx, target_is_pinned):
    """Return a new images list with source_indices moved to insert_idx and
    their pin state updated to target_is_pinned.

    Mutates img.pinned on moved items in place — the returned list references
    the same ImageItem objects as the input (consistent with _toggle_pin).

    Preserves the 'pinned tiles contiguous at the head' invariant by
    rebuilding the final list as pinned + unpinned. source_indices may span
    the pinned/non-pinned boundary only if the caller already filtered by
    zone.
    """
    # Collect moved items; set their pinned state.
    moved = [images[i] for i in source_indices]
    for img in moved:
        img.pinned = target_is_pinned

    # Remaining = images with moved items removed (preserve order).
    excluded = set(source_indices)
    remaining = [img for i, img in enumerate(images) if i not in excluded]

    # Insertion index is in the space of the ORIGINAL list; translate to the
    # remaining list by subtracting how many source_indices are before it.
    before = sum(1 for i in source_indices if i < insert_idx)
    adj_insert = max(0, insert_idx - before)
    adj_insert = min(adj_insert, len(remaining))

    combined = remaining[:adj_insert] + moved + remaining[adj_insert:]

    # Normalize: pinned contiguous at head.
    pinned = [img for img in combined if img.pinned]
    unpinned = [img for img in combined if not img.pinned]
    return pinned + unpinned
```

- [ ] **Step 2: Remove originals from `__init__.py`**

In `ui/editor_panel/__init__.py`:
- Remove `import json` if it is no longer used elsewhere in the file (grep within the file).
- Remove the `TILE_DRAG_MIME = ...` assignment and its preceding comment block.
- Remove `def _decode_tile_drag_payload(...)`.
- Remove `def _compute_insertion_index(...)`.
- Remove `def _filter_selection_by_zone(...)`.
- Remove `def _apply_tile_drop(...)`.

- [ ] **Step 3: Add re-exports to `__init__.py`**

Add:
```python
from ui.editor_panel.tile_drag import (
    TILE_DRAG_MIME,
    _decode_tile_drag_payload,
    _compute_insertion_index,
    _filter_selection_by_zone,
    _apply_tile_drop,
)
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_tile_drag.py tests/ -q`
Expected: all green (test_tile_drag exercises three of the helpers directly).

- [ ] **Step 5: Import smoke**

Run:
```bash
python -c "from ui.editor_panel import TILE_DRAG_MIME, _decode_tile_drag_payload, _compute_insertion_index, _filter_selection_by_zone, _apply_tile_drop; print(TILE_DRAG_MIME)"
```
Expected: `application/x-drawer-tile-indices`

- [ ] **Step 6: App launch check**

Run: `python main.py` → open editor in grid view, drag a tile in the pinned zone, drag to unpin, drag multi-selection. All drag flows behave as before. Close.

- [ ] **Step 7: Commit**

```bash
git add ui/editor_panel/tile_drag.py ui/editor_panel/__init__.py
git commit -m "refactor(editor_panel): extract tile drag helpers to tile_drag.py

Pure-Python helpers for drag MIME payload, insertion geometry, selection
zone filter, and reorder logic."
```

---

## Task 5: Extract `pixmap_loader.py`

Move the `PixmapLoader` QThread into its own module.

**Files:**
- Create: `ui/editor_panel/pixmap_loader.py`
- Modify: `ui/editor_panel/__init__.py`

- [ ] **Step 1: Create `ui/editor_panel/pixmap_loader.py`**

Write `ui/editor_panel/pixmap_loader.py`:

```python
# ui/editor_panel/pixmap_loader.py
"""Background pixmap loader thread for the editor grid."""

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QImage

from ui.scales import S


class PixmapLoader(QThread):
    """Load images from disk in a background thread."""
    loaded = pyqtSignal(str, QImage)

    def __init__(self, paths, max_size=None):
        super().__init__()
        self._paths = paths
        self._max = max_size if max_size is not None else S.GRID_MAX
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        for path in self._paths:
            if self._cancel:
                return
            img = QImage(path)
            if not img.isNull():
                img = img.scaled(
                    self._max, self._max,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.loaded.emit(path, img)
```

- [ ] **Step 2: Remove original class from `__init__.py`**

Remove the `class PixmapLoader(QThread):` block and its docstring comment header from `ui/editor_panel/__init__.py`.

- [ ] **Step 3: Add re-export to `__init__.py`**

Add:
```python
from ui.editor_panel.pixmap_loader import PixmapLoader
```

- [ ] **Step 4: Check imports still needed**

Open `ui/editor_panel/__init__.py`. Check whether `QThread` and `QImage` are still imported and whether they are still used elsewhere in the file. `QThread` is only used by `PixmapLoader` — remove from the imports. `QImage` is still used by `_on_pixmap_loaded` in `EditorPanel` — keep.

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/ -q`
Expected: all green.

- [ ] **Step 6: Import smoke**

Run: `python -c "from ui.editor_panel import PixmapLoader; print('OK')"`
Expected: `OK`

- [ ] **Step 7: App launch check**

Run: `python main.py` → grid view loads pixmaps from disk asynchronously (thumbnails appear). Close.

- [ ] **Step 8: Commit**

```bash
git add ui/editor_panel/pixmap_loader.py ui/editor_panel/__init__.py
git commit -m "refactor(editor_panel): extract PixmapLoader to pixmap_loader.py"
```

---

## Task 6: Extract `tile_widgets.py`

Move the four tile widget classes (`_ColorLine`, `ClickableLabel`, `_PinPlaceholderRow`, `_PinPlaceholderTile`) into their own module. This is the largest extraction before the final move and the one with highest circular-import risk.

**Files:**
- Create: `ui/editor_panel/tile_widgets.py`
- Modify: `ui/editor_panel/__init__.py`

- [ ] **Step 1: Create `ui/editor_panel/tile_widgets.py` with all four classes**

Locate the four class definitions in the current `ui/editor_panel/__init__.py` using:

```bash
grep -n "^class " ui/editor_panel/__init__.py
```

Expected matches: `_ColorLine(QWidget)`, `ClickableLabel(QLabel)`, `_PinPlaceholderRow(QLabel)`, `_PinPlaceholderTile(QLabel)`, `EditorPanel(QWidget)`. Copy the four non-`EditorPanel` class bodies verbatim (including docstrings and any blank lines between them) into a new file `ui/editor_panel/tile_widgets.py` with this header:

```python
# ui/editor_panel/tile_widgets.py
"""Tile widget classes: color line, clickable label, drop placeholders."""

import qtawesome as qta
from PyQt6.QtWidgets import QWidget, QLabel, QListWidget
from PyQt6.QtGui import QPixmap, QColor, QPainter
from PyQt6.QtCore import Qt

from ui.icons import Icons
from ui.scales import S
from ui.editor_panel.tile_drag import (
    TILE_DRAG_MIME,
    _decode_tile_drag_payload,
    _apply_tile_drop,
    _filter_selection_by_zone,
)


# <<< paste _ColorLine, ClickableLabel, _PinPlaceholderRow,
# <<< _PinPlaceholderTile class bodies here, in that order,
# <<< byte-identical to the originals in __init__.py
```

The class bodies must be byte-identical to what they were before the move. Do not edit them in this task.

**Circular-import check:** `ClickableLabel._find_editor` walks `self.parent()` at runtime. It does not import `EditorPanel` statically. Good — no circular dependency.

- [ ] **Step 2: Remove the four class definitions from `__init__.py`**

Remove from `ui/editor_panel/__init__.py`:
- `class _ColorLine(QWidget): ...` and its preceding comments.
- `class ClickableLabel(QLabel): ...` and its header comment block.
- `class _PinPlaceholderRow(QLabel): ...`
- `class _PinPlaceholderTile(QLabel): ...`

- [ ] **Step 3: Add re-exports to `__init__.py`**

Add:
```python
from ui.editor_panel.tile_widgets import (
    _ColorLine,
    ClickableLabel,
    _PinPlaceholderRow,
    _PinPlaceholderTile,
)
```

- [ ] **Step 4: Clean up `__init__.py` imports no longer used**

After step 3, grep the file and remove any Qt / qtawesome imports that are now unreferenced in `__init__.py`. Expected removals (verify each by grep before deleting):
- `qtawesome as qta` — still used by `EditorPanel` for icons; keep.
- `QListWidget` — still used by `EditorPanel`; keep.
- `QPixmap`, `QColor`, `QPainter` — still used by `EditorPanel`; keep.

If unsure, leave it — unused imports are harmless and will be swept in Task 7.

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/ -q`
Expected: all green.

- [ ] **Step 6: Import smoke**

Run:
```bash
python -c "from ui.editor_panel import _ColorLine, ClickableLabel, _PinPlaceholderRow, _PinPlaceholderTile; print('OK')"
```
Expected: `OK`

- [ ] **Step 7: App launch check**

Run: `python main.py`. Full grid interaction: add images, click tiles, shift-click, ctrl-click, drag-reorder, drag to pinned zone (placeholder visible when pinned zone empty), right-click context menu. Switch list/grid modes. Close.

- [ ] **Step 8: Commit**

```bash
git add ui/editor_panel/tile_widgets.py ui/editor_panel/__init__.py
git commit -m "refactor(editor_panel): extract tile widget classes to tile_widgets.py

Moves _ColorLine, ClickableLabel, _PinPlaceholderRow, _PinPlaceholderTile.
ClickableLabel._find_editor continues to discover the EditorPanel via
parent() walk, avoiding static imports."
```

---

## Task 7: Move `EditorPanel` → `panel.py`

Last step. `EditorPanel` moves out of `__init__.py` into `panel.py`. `__init__.py` becomes a pure re-export file.

**Files:**
- Create: `ui/editor_panel/panel.py`
- Modify: `ui/editor_panel/__init__.py` (final pure-re-export form)

- [ ] **Step 1: Create `ui/editor_panel/panel.py` with the EditorPanel class**

After Tasks 2–6, the current `ui/editor_panel/__init__.py` contains: (a) a module docstring and top-of-file imports, (b) six sibling-re-export lines, and (c) the `EditorPanel` class body (starting at `class EditorPanel(QWidget):` and running to end of file).

Locate (c):

```bash
grep -n "^class EditorPanel" ui/editor_panel/__init__.py
```

Copy the `EditorPanel` class body verbatim (from its `class EditorPanel(QWidget):` line to the end of the file, plus any preceding comment banner like `# ---- EditorPanel ----`) into a new file `ui/editor_panel/panel.py` with this header:

```python
# ui/editor_panel/panel.py
"""EditorPanel — reusable image editor panel widget for Drawer."""

import os
from collections import OrderedDict

import qtawesome as qta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QFileDialog, QSlider,
    QScrollArea, QStackedWidget, QMessageBox, QSizePolicy,
)
from PyQt6.QtGui import QPixmap, QIcon, QColor, QBrush, QImage, QPainter, QPainterPath, QPalette, QDrag
from PyQt6.QtCore import Qt, QRectF, pyqtSignal, QSize, QTimer, QMimeData, QPoint

from core.constants import SUPPORTED_FORMATS
from core.file_utils import filter_image_files, scan_folder, dedup_paths
from core.models import ImageItem, DEFAULT_TIMER_SECONDS
from core.timer_logic import format_time, short_label
from ui.theme import _mix, _darken
from ui.scales import S
from ui.icons import Icons
from ui.widgets import make_icon_btn

from ui.editor_panel.tile_drag import (
    TILE_DRAG_MIME,
    _decode_tile_drag_payload,
    _compute_insertion_index,
    _filter_selection_by_zone,
    _apply_tile_drop,
)
from ui.editor_panel.flow_layout import _flow_position, _flow_position_with_gaps
from ui.editor_panel.sort import _sort_group_items
from ui.editor_panel.pixmap_loader import PixmapLoader
from ui.editor_panel.tile_widgets import (
    _ColorLine,
    ClickableLabel,
    _PinPlaceholderRow,
    _PinPlaceholderTile,
)


# <<< paste the EditorPanel class body here, byte-identical to the
# <<< original in __init__.py
```

The class body must be byte-identical. Do not edit it in this task.

Notes on the import list vs. the original:
- `json` is no longer needed here — it is used by `tile_drag.py`.
- `QThread` is no longer needed — it is used by `pixmap_loader.py`.
- The ten `from ui.editor_panel.*` imports are new and reach into the sibling modules the previous tasks created.

- [ ] **Step 2: Replace `__init__.py` with the final re-export body**

Overwrite `ui/editor_panel/__init__.py` with exactly this content:

```python
# ui/editor_panel/__init__.py
"""EditorPanel package — split for maintainability.

Public surface preserved from the pre-split ui/editor_panel.py.
"""

from ui.editor_panel.tile_drag import (
    TILE_DRAG_MIME,
    _decode_tile_drag_payload,
    _compute_insertion_index,
    _filter_selection_by_zone,
    _apply_tile_drop,
)
from ui.editor_panel.flow_layout import _flow_position, _flow_position_with_gaps
from ui.editor_panel.sort import _sort_group_items
from ui.editor_panel.pixmap_loader import PixmapLoader
from ui.editor_panel.tile_widgets import (
    _ColorLine,
    ClickableLabel,
    _PinPlaceholderRow,
    _PinPlaceholderTile,
)
from ui.editor_panel.panel import EditorPanel

__all__ = [
    "EditorPanel",
    "ClickableLabel",
    "PixmapLoader",
    "TILE_DRAG_MIME",
    "_sort_group_items",
    "_compute_insertion_index",
    "_filter_selection_by_zone",
    "_apply_tile_drop",
    "_PinPlaceholderRow",
    "_PinPlaceholderTile",
]
```

- [ ] **Step 3: Run tests**

Run: `python -m pytest tests/ -q`
Expected: all green.

- [ ] **Step 4: Import smoke**

Run:
```bash
python -c "from ui.editor_panel import EditorPanel, _sort_group_items, _compute_insertion_index, _filter_selection_by_zone, _apply_tile_drop, TILE_DRAG_MIME, ClickableLabel, PixmapLoader, _PinPlaceholderRow, _PinPlaceholderTile; print('OK')"
```
Expected: `OK`

- [ ] **Step 5: Line-count check**

Run: `wc -l ui/editor_panel/*.py`
Expected: no single file above ~1300 lines; sum roughly equal to the original 1787.

- [ ] **Step 6: `git log --follow` sanity**

Run: `git log --follow --oneline ui/editor_panel/panel.py | head`
Expected: history traces back through `ui/editor_panel/__init__.py` (from Task 1) to the original `ui/editor_panel.py`.

- [ ] **Step 7: App launch check**

Run: `python main.py` → full usage across modes, as in Task 8 below.

- [ ] **Step 8: Commit**

```bash
git add ui/editor_panel/panel.py ui/editor_panel/__init__.py
git commit -m "refactor(editor_panel): move EditorPanel class to panel.py

__init__.py becomes a pure re-export module. All external import paths
(ui.editor_panel.EditorPanel, _sort_group_items, etc.) remain stable."
```

---

## Task 8: Full manual smoke test

No code changes. Validate end-to-end that the split introduced no regressions. If any step fails, diagnose which prior task's change is responsible and revert that task only.

- [ ] **Step 1: Launch**

Run: `python main.py`
Expected: app launches, settings window appears if first-run flow.

- [ ] **Step 2: Open editor — detached and docked**

Open the editor via settings → verify it works in both detached-window and docked positions. Switch between them.

- [ ] **Step 3: Add images**

- Click "Add files" button — pick a few images. Verify they appear.
- Click "Add folder" — pick a folder with images. Verify scan and dedup.
- Drag-drop a file from Windows Explorer onto the editor. Verify it adds.

- [ ] **Step 4: List view interaction**

Switch to list view. Click a tile — selection updates. Shift-click a second — range selected. Ctrl-click a third — toggle. Delete key — selected rows deleted.

- [ ] **Step 5: Grid view interaction**

Switch to grid view. Same selection actions as list. Zoom slider — tiles resize, reflow. Right-click a tile — context menu appears with pin/unpin, set timer, move-to-group options.

- [ ] **Step 6: Pin / unpin / pinned placeholder**

- Pin a tile via context menu. Verify it moves to the pinned zone at the top.
- Unpin it. Verify the pinned zone shows the "drop here to pin" placeholder when empty.
- Drag an unpinned tile into the placeholder. Verify it pins at index 0.

- [ ] **Step 7: Drag reorder**

- Drag a tile within the list view to a new position. Verify order updates.
- Drag a tile within the grid view. Verify order + reflow.
- Multi-select in grid, drag the whole block. Verify all move together.
- Drag pinned → unpinned and vice versa — verify pin state updates.

- [ ] **Step 8: Class mode**

Toggle class mode. Verify selection is disabled, context menu is disabled, delete key is no-op. Toggle back — behaviors return.

- [ ] **Step 9: Persistence**

Clear the list. Add a few images. Close the app. Relaunch. Verify the list is restored.

- [ ] **Step 10: Confirmation**

If every step above behaved identically to pre-split behavior, the task is done. If any step deviated, revert the implicated extraction task (most likely Task 6 for widget-interaction bugs, Task 4 for drag math, Task 7 for EditorPanel move) and investigate.

No commit at this step — it is pure validation.

---

## Post-flight

- [ ] **Confirm all tests pass**

Run: `python -m pytest tests/ -q`
Expected: all green.

- [ ] **Confirm branch history is linear**

Run: `git log --oneline main..HEAD`
Expected: 7 commits on `chore/split-editor-panel` — one per task 1–7 (Task 8 is validation, no commit).

- [ ] **Run simplify skill**

Per CLAUDE.md step 9: after finishing a feature, run the `simplify` skill on the diff. If overkill, tell Oksana explicitly.

- [ ] **Hand off to Oksana**

Ask Oksana to `python main.py` and run the same smoke tests. Only push and open PR after her approval, per CLAUDE.md step 10.
