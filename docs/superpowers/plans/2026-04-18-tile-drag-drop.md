# Tile Drag-Drop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add zone-based drag-drop to the quick-mode editor (tile view and list view) so users can reorder tiles and bulk pin/unpin by dragging across the pinned↔non-pinned boundary. Class mode loses drag entirely. Bundled cosmetic + bug fixes.

**Architecture:** Pure-Python helpers for insertion-index, zone filtering, and drop application (unit-testable without Qt). Tile view gets custom `QDrag` via `ClickableLabel.mouseMoveEvent` and a dispatching `dropEvent` on the grid container that distinguishes internal tile drags (custom MIME) from external file drops (URL MIME). List view uses monkey-patched `dropEvent` on `QListWidget` instances with the same zone rules. Empty pinned zone gets a dashed-outline placeholder widget (tile or row) that accepts drops and pins.

**Tech Stack:** Python 3.14, PyQt6, pytest. Drag-drop is Qt (`QDrag`, `QMimeData`); helper functions are pure Python.

**Spec:** `docs/superpowers/specs/2026-04-18-tile-drag-drop-design.md`

---

## File Structure

- **Create:** `tests/test_tile_drag.py` — unit tests for the pure-Python helpers.
- **Modify:** `ui/editor_panel.py` — all drag-drop, placeholder, polish changes land here. Already the locus of the editor; nothing else needs to move.
- **No change:** `core/play_order.py`, `core/models.py`, `ui/settings_window.py`, `ui/image_editor_window.py`.

---

### Task 1: Pure-Python helper functions (TDD)

**Files:**
- Create: `tests/test_tile_drag.py`
- Modify: `ui/editor_panel.py` (add three module-level helpers)

Three module-level pure-Python helpers. Tested without Qt. Everything else builds on them.

- [ ] **Step 1: Create `tests/test_tile_drag.py` with failing tests**

```python
"""Unit tests for tile-drag helpers — pure Python, no Qt."""

from core.models import ImageItem
from ui.editor_panel import (
    _compute_insertion_index,
    _filter_selection_by_zone,
    _apply_tile_drop,
)


def _img(path, pinned=False, timer=60):
    return ImageItem(path=path, timer=timer, pinned=pinned)


# ------------------------------------------------------------------
# _compute_insertion_index
# ------------------------------------------------------------------

def test_insertion_index_empty_grid():
    assert _compute_insertion_index((50, 50), []) == 0


def test_insertion_index_before_first_tile():
    rects = [(0, 0, 0, 80, 80), (1, 90, 0, 80, 80)]  # (idx, x, y, w, h)
    assert _compute_insertion_index((5, 40), rects) == 0


def test_insertion_index_between_two_tiles():
    rects = [(0, 0, 0, 80, 80), (1, 90, 0, 80, 80)]
    # Cursor past midline of first tile → insert between (index 1)
    assert _compute_insertion_index((50, 40), rects) == 1


def test_insertion_index_after_last_tile():
    rects = [(0, 0, 0, 80, 80), (1, 90, 0, 80, 80)]
    assert _compute_insertion_index((200, 40), rects) == 2


def test_insertion_index_second_row():
    rects = [
        (0, 0, 0, 80, 80),
        (1, 90, 0, 80, 80),
        (2, 0, 90, 80, 80),
        (3, 90, 90, 80, 80),
    ]
    # Cursor on second row, between the two tiles → index 3
    assert _compute_insertion_index((50, 130), rects) == 3


# ------------------------------------------------------------------
# _filter_selection_by_zone
# ------------------------------------------------------------------

def test_filter_selection_keeps_same_zone():
    images = [_img("a", pinned=True), _img("b", pinned=True),
              _img("c"), _img("d")]
    # Selection: indices 0, 1, 2 (two pinned + one non-pinned)
    # Source zone: pinned (index 0 pressed)
    assert _filter_selection_by_zone([0, 1, 2], source_is_pinned=True,
                                     images=images) == [0, 1]


def test_filter_selection_keeps_non_pinned():
    images = [_img("a", pinned=True), _img("b"), _img("c"), _img("d")]
    # Selection 0, 2, 3 — source non-pinned (index 2 pressed)
    assert _filter_selection_by_zone([0, 2, 3], source_is_pinned=False,
                                     images=images) == [2, 3]


def test_filter_selection_single():
    images = [_img("a"), _img("b")]
    assert _filter_selection_by_zone([0], source_is_pinned=False,
                                     images=images) == [0]


# ------------------------------------------------------------------
# _apply_tile_drop
# ------------------------------------------------------------------

def test_apply_drop_within_non_pinned_zone():
    """Reorder within non-pinned zone. No pin changes."""
    images = [_img("p", pinned=True), _img("a"), _img("b"), _img("c")]
    # Move "c" (index 3) to just before "a" — insert index 1 in non-pinned zone
    new = _apply_tile_drop(images, source_indices=[3], insert_idx=1,
                           target_is_pinned=False)
    assert [i.path for i in new] == ["p", "c", "a", "b"]
    assert [i.pinned for i in new] == [True, False, False, False]


def test_apply_drop_within_pinned_zone():
    """Reorder within pinned zone. No pin changes."""
    images = [_img("p1", pinned=True), _img("p2", pinned=True),
              _img("p3", pinned=True), _img("a")]
    # Move "p3" to position 0 among pinned
    new = _apply_tile_drop(images, source_indices=[2], insert_idx=0,
                           target_is_pinned=True)
    assert [i.path for i in new] == ["p3", "p1", "p2", "a"]
    assert [i.pinned for i in new] == [True, True, True, False]


def test_apply_drop_non_pinned_into_pinned_zone():
    """Cross-zone: non-pinned → pinned. Item becomes pinned."""
    images = [_img("p", pinned=True), _img("a"), _img("b")]
    # Drop "b" (index 2) into pinned zone at insert_idx 1 (after "p")
    new = _apply_tile_drop(images, source_indices=[2], insert_idx=1,
                           target_is_pinned=True)
    assert [i.path for i in new] == ["p", "b", "a"]
    assert [i.pinned for i in new] == [True, True, False]


def test_apply_drop_pinned_into_non_pinned_zone():
    """Cross-zone: pinned → non-pinned. Item becomes unpinned."""
    images = [_img("p1", pinned=True), _img("p2", pinned=True),
              _img("a"), _img("b")]
    # Drop "p1" (index 0) into non-pinned zone at insert_idx 3
    new = _apply_tile_drop(images, source_indices=[0], insert_idx=3,
                           target_is_pinned=False)
    assert [i.path for i in new] == ["p2", "a", "p1", "b"]
    assert [i.pinned for i in new] == [True, False, False, False]


def test_apply_drop_multi_select_non_pinned_into_pinned():
    """Multi-select cross-zone drop. All become pinned."""
    images = [_img("p", pinned=True), _img("a"), _img("b"), _img("c")]
    new = _apply_tile_drop(images, source_indices=[1, 2], insert_idx=1,
                           target_is_pinned=True)
    # "a" and "b" join the pinned block after "p"
    assert [i.path for i in new] == ["p", "a", "b", "c"]
    assert [i.pinned for i in new] == [True, True, True, False]


def test_apply_drop_preserves_pinned_contiguous_invariant():
    """After any drop, pinned tiles are contiguous at the head."""
    images = [_img("p1", pinned=True), _img("a"), _img("p2", pinned=True),
              _img("b")]
    # (Pathological starting state — pinned not contiguous. Apply a drop and
    # verify the result is normalized.)
    new = _apply_tile_drop(images, source_indices=[3], insert_idx=4,
                           target_is_pinned=False)
    # All pinned come first in result regardless of input order
    pinned = [i for i in new if i.pinned]
    unpinned = [i for i in new if not i.pinned]
    assert new == pinned + unpinned


def test_apply_drop_same_position_noop():
    """Dropping at the exact source position yields the original list."""
    images = [_img("p", pinned=True), _img("a"), _img("b")]
    new = _apply_tile_drop(images, source_indices=[1], insert_idx=1,
                           target_is_pinned=False)
    assert [i.path for i in new] == ["p", "a", "b"]
```

- [ ] **Step 2: Run tests — verify they fail with ImportError**

Run: `python -m pytest tests/test_tile_drag.py -v`
Expected: ImportError on `_compute_insertion_index`, `_filter_selection_by_zone`, `_apply_tile_drop` — all three don't exist yet.

- [ ] **Step 3: Add `_compute_insertion_index` to `ui/editor_panel.py`**

Add after the existing `_sort_group_items` function (around line 54). Put it with the other module-level helpers before the class definitions.

```python
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
    remaining = [img for i, img in enumerate(images) if i not in set(source_indices)]

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

- [ ] **Step 4: Run tests — all pass**

Run: `python -m pytest tests/test_tile_drag.py -v`
Expected: all 14 tests pass.

Run full suite: `python -m pytest -q`
Expected: no regressions (total count should be 160 + 14 = 174 tests).

- [ ] **Step 5: Commit**

```bash
git add ui/editor_panel.py tests/test_tile_drag.py
git commit -m "$(cat <<'EOF'
feat: add tile-drag helpers — insertion-index, zone-filter, drop-apply

Three pure-Python helpers for tile drag-drop (no Qt):
- _compute_insertion_index: cursor pos + tile rects → list insertion idx.
- _filter_selection_by_zone: drop cross-zone members of a selection.
- _apply_tile_drop: new images list with reorder + pin-flip applied,
  preserving the 'pinned contiguous at head' invariant.

Unit tests cover all four zone combinations (within-pin, within-non-pin,
pinned→non, non→pinned), multi-select cross-zone, pathological input
normalization, and same-position no-op.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Quick cosmetic fixes (pin color, selection frame corners, class-mode list drag disable)

**Files:**
- Modify: `ui/editor_panel.py`

Three independent small changes. Commit each separately for reviewable history.

- [ ] **Step 1: Pin icon color → accent**

In `ui/editor_panel.py`, find both occurrences of `pin_icon = qta.icon(Icons.TOPMOST_ON, color=t.text_hint)` (one in `_rebuild_grid`, one in the zoom-handler re-render).

Replace `color=t.text_hint` with `color=t.accent` in both.

Verify with grep after editing:
```
grep -n "TOPMOST_ON" ui/editor_panel.py
```
Expected: both matches show `color=t.accent`.

- [ ] **Step 2: Sanity check + commit**

Run: `python -c "from ui.editor_panel import EditorPanel; print('OK')"` → `OK`.
Run: `python -m pytest -q` → all pass.

```bash
git add ui/editor_panel.py
git commit -m "$(cat <<'EOF'
fix: tile-view pin icon uses accent color

Previously the tile-view pin icon used t.text_hint (muted grey) while
list-view pinned entries used t.accent. Unify both views on t.accent so
the pin indicator is legible at a glance. Size formula unchanged —
the 20px cap remains deliberate (prevents the icon from dominating tiles
at max zoom).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 3: Selection frame rounded corners**

In `_select_tile` (around line 814):

```python
    def _select_tile(self, lbl):
        t = self.theme
        self._selected_tiles.add(lbl)
        lbl._selected = True
        lbl.setStyleSheet(f"border: {S.EDITOR_BORDER_SELECTED}px solid {t.border_active};")
```

Change the stylesheet to include a `border-radius` matching the tile rounded-corner radius. The rounded-tile code uses `addRoundedRect(..., 3, 3)` (see existing code around line 764-766 in the rounded-pixmap block). Use `3px`:

```python
    def _select_tile(self, lbl):
        t = self.theme
        self._selected_tiles.add(lbl)
        lbl._selected = True
        lbl.setStyleSheet(
            f"border: {S.EDITOR_BORDER_SELECTED}px solid {t.border_active}; "
            f"border-radius: 3px;"
        )
```

Also update `_deselect_tile` (around line 820) so the reserve/non-reserve branches include matching border-radius where they set a visible border:

```python
    def _deselect_tile(self, lbl):
        self._selected_tiles.discard(lbl)
        lbl._selected = False
        # Restore original border state
        idx = lbl.property("img_idx")
        if idx is not None and idx < len(self.images):
            img = self.images[idx]
            t = self.theme
            is_reserve = img.timer == 0
            if is_reserve:
                lbl.setStyleSheet(
                    f"border: {S.EDITOR_BORDER_DASHED}px dashed {t.text_hint}; "
                    f"border-radius: 3px;"
                )
            else:
                lbl.setStyleSheet("border: none;")
        else:
            lbl.setStyleSheet("")
```

- [ ] **Step 4: Sanity check + commit**

Run: `python -m pytest -q` → all pass.

```bash
git add ui/editor_panel.py
git commit -m "$(cat <<'EOF'
fix: selection frame matches tile rounded corners

Tile pixmaps are clipped to a 3px rounded rect. Selection/reserve
border stylesheets now carry border-radius: 3px so the frame corners
follow the tile corners instead of showing square outlines.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 5: Class-mode list drag disable**

In `_rebuild_list` (around line 528), find:

```python
            lw.setDragDropMode(QListWidget.DragDropMode.InternalMove)
```

Replace with a mode check:

```python
            if self._timer_mode == "quick":
                lw.setDragDropMode(QListWidget.DragDropMode.InternalMove)
            else:
                lw.setDragDropMode(QListWidget.DragDropMode.NoDragDrop)
```

- [ ] **Step 6: Sanity check + commit**

Run: `python -m pytest -q` → all pass.

```bash
git add ui/editor_panel.py
git commit -m "$(cat <<'EOF'
feat: list-view drag disabled in class mode

Spec #3 established 'no per-image manual control in class mode.'
The remaining within-tier InternalMove drag on list widgets
contradicted that. Set DragDropMode.NoDragDrop when timer_mode ==
'class'; keep InternalMove in quick mode.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Selection clears on empty-area click

**Files:**
- Modify: `ui/editor_panel.py`

Users expect clicking empty grid/list space to clear the current selection. Add handlers on the grid container and list scroll widgets.

- [ ] **Step 1: Add `_clear_selection` helper on `EditorPanel`**

Find the grid selection section (around line 805). Add a helper method that clears both tile and list-item selections:

```python
    def _clear_selection(self):
        """Clear both tile-view and list-view selections."""
        # Tile view
        if self._selected_tiles:
            for lbl in list(self._selected_tiles):
                self._deselect_tile(lbl)
            self._selected_tiles.clear()
        # List view — clear any QListWidget selections
        for _, lw in self._list_groups:
            lw.clearSelection()
```

- [ ] **Step 2: Wire grid container `mousePressEvent` to clear selection on empty click**

At the end of `_build_ui` or in `_rebuild_grid`, override `mousePressEvent` on `self._grid_container` so that a click not hitting any tile clears selection.

Find the `_grid_container` creation (around line 239). Immediately after:

```python
        self._grid_container = QWidget()
        self._grid_layout = QVBoxLayout(self._grid_container)
        self._grid_layout.setContentsMargins(0, 0, 0, 0)
        self._grid_layout.setSpacing(S.GRID_SPACING)
        self._grid_layout.addStretch()
        self._grid_scroll.setWidget(self._grid_container)
```

Add the mousePressEvent wiring via monkey-patch (matching the existing `self._grid_scroll.dragEnterEvent = ...` pattern used elsewhere):

```python
        # Click on empty grid area clears selection.
        def _grid_empty_click(event):
            # If click didn't land on a tile (no child widget at that pos),
            # clear selection. Otherwise let the child handle it normally.
            child = self._grid_container.childAt(event.pos())
            if child is None:
                self._clear_selection()
            # Call default handler
            QWidget.mousePressEvent(self._grid_container, event)

        self._grid_container.mousePressEvent = _grid_empty_click
```

Do the same for `self._list_container`:

```python
        # Click on empty list area clears selection.
        def _list_empty_click(event):
            child = self._list_container.childAt(event.pos())
            if child is None:
                self._clear_selection()
            QWidget.mousePressEvent(self._list_container, event)

        self._list_container.mousePressEvent = _list_empty_click
```

- [ ] **Step 3: Sanity check + manual test**

Run: `python -c "from ui.editor_panel import EditorPanel; print('OK')"` → `OK`.
Run: `python -m pytest -q` → all pass.

- [ ] **Step 4: Commit**

```bash
git add ui/editor_panel.py
git commit -m "$(cat <<'EOF'
fix: click on empty grid/list area clears selection

Clicking an image selected it with an accent frame, but clicking
empty space left the selection in place — pre-existing UX gap.
Added mousePressEvent handlers on the grid and list containers that
clear selection when the click doesn't land on any child widget.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Tile view drag source

**Files:**
- Modify: `ui/editor_panel.py`

Teach `ClickableLabel` to initiate a `QDrag` when the user presses + moves past a 5px threshold. Only active in quick mode.

- [ ] **Step 1: Add QDrag imports**

At the top of `ui/editor_panel.py`, add to the existing `PyQt6.QtGui` import:

```python
from PyQt6.QtGui import (
    QPixmap, QIcon, QColor, QBrush, QImage, QPainter, QPainterPath,
    QPalette, QDrag,
)
```

And to `PyQt6.QtCore`:

```python
from PyQt6.QtCore import Qt, QRectF, QMimeData, QPoint, pyqtSignal, QSize, QTimer, QThread
```

Add `import json` at the top near the `import os` line.

- [ ] **Step 2: Define MIME constant**

Near the top of the module, after imports and before `_ColorLine`, add:

```python
TILE_DRAG_MIME = "application/x-drawer-tile-indices"
```

- [ ] **Step 3: Extend `ClickableLabel` with drag-source logic**

Replace the existing `ClickableLabel` (lines 92–117) with:

```python
class ClickableLabel(QLabel):
    """QLabel with click-to-select + drag-source support for grid tiles."""

    DRAG_THRESHOLD = 5  # pixels

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected = False
        self._press_pos = None
        self._drag_started = False

    def _find_editor(self):
        w = self.parent()
        while w is not None:
            if hasattr(w, "_on_tile_click"):
                return w
            w = w.parent()
        return None

    def mousePressEvent(self, event):
        editor = self._find_editor()
        if editor is None:
            return

        if event.button() == Qt.MouseButton.RightButton:
            editor._show_tile_context_menu(self, event.globalPosition().toPoint())
            return

        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.pos()
            self._drag_started = False

        mods = event.modifiers()
        ctrl = bool(mods & Qt.KeyboardModifier.ControlModifier)
        shift = bool(mods & Qt.KeyboardModifier.ShiftModifier)
        editor._on_tile_click(self, ctrl, shift)

    def mouseMoveEvent(self, event):
        if self._press_pos is None or self._drag_started:
            return
        editor = self._find_editor()
        if editor is None or getattr(editor, "_timer_mode", "quick") != "quick":
            return
        if (event.pos() - self._press_pos).manhattanLength() < self.DRAG_THRESHOLD:
            return

        # Build the list of source indices: the selection if this tile is
        # part of it, else just this tile. Then filter to same-zone.
        my_idx = self.property("img_idx")
        if my_idx is None or my_idx >= len(editor.images):
            return
        my_is_pinned = bool(editor.images[my_idx].pinned)

        if self in editor._selected_tiles:
            sel_indices = [
                lbl.property("img_idx")
                for lbl in editor._selected_tiles
                if lbl.property("img_idx") is not None
            ]
            indices = _filter_selection_by_zone(sel_indices, my_is_pinned,
                                                editor.images)
            if my_idx not in indices:
                indices = [my_idx]
        else:
            indices = [my_idx]

        self._drag_started = True
        editor._start_tile_drag(self, indices, my_is_pinned)

    def mouseReleaseEvent(self, event):
        self._press_pos = None
        self._drag_started = False
```

- [ ] **Step 4: Add `_start_tile_drag` method on `EditorPanel`**

In the `EditorPanel` class, near the selection/drag handling (around line 805), add:

```python
    def _start_tile_drag(self, source_lbl, source_indices, source_is_pinned):
        """Start a QDrag from the pressed tile. Carries source_indices as
        JSON in the TILE_DRAG_MIME payload."""
        if not source_indices:
            return
        drag = QDrag(source_lbl)
        mime = QMimeData()
        mime.setData(
            TILE_DRAG_MIME,
            json.dumps({
                "indices": source_indices,
                "source_is_pinned": source_is_pinned,
            }).encode("utf-8"),
        )
        drag.setMimeData(mime)
        # Use the source tile's pixmap (scaled down) as the drag preview
        pix = source_lbl.pixmap()
        if pix and not pix.isNull():
            drag.setPixmap(pix.scaled(
                pix.width() * 3 // 5, pix.height() * 3 // 5,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))
            drag.setHotSpot(QPoint(pix.width() // 6, pix.height() // 6))

        drag.exec(Qt.DropAction.MoveAction)
```

- [ ] **Step 5: Sanity check + commit**

Run: `python -c "from ui.editor_panel import EditorPanel, ClickableLabel, TILE_DRAG_MIME; print('OK')"` → `OK`.
Run: `python -m pytest -q` → all 174 pass.

```bash
git add ui/editor_panel.py
git commit -m "$(cat <<'EOF'
feat: ClickableLabel initiates QDrag on move past threshold

Tile drag source: mousePressEvent stores press position; mouseMoveEvent
starts a QDrag once movement exceeds 5px, carrying the selected tile
indices (or just the pressed tile if none selected) as JSON under
a custom MIME type (application/x-drawer-tile-indices). Filters
multi-select by zone so only same-zone members participate. Only
active in quick mode.

Drop target wiring arrives in the next task.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Tile view drop target

**Files:**
- Modify: `ui/editor_panel.py`

The existing `_drag_enter` and `_drop_event` already accept URL drops (external file adds). Extend them to dispatch by MIME: URL → existing handler; `TILE_DRAG_MIME` → new internal-drop handler.

- [ ] **Step 1: Extract the existing external-drop code into its own method**

Find `_drop_event` (around line 1021). Rename it to `_handle_external_drop` (it handles external file drops only).

Original:

```python
    def _drop_event(self, event):
        urls = event.mimeData().urls()
        added = False
        timer = self._default_add_timer()
        for url in urls:
            if url.isLocalFile():
                path = url.toLocalFile()
                if os.path.isdir(path):
                    for p in dedup_paths(scan_folder(path), self.images):
                        self.images.append(ImageItem(path=p, timer=timer))
                        added = True
                else:
                    if filter_image_files([path]) and path not in {i.path for i in self.images}:
                        self.images.append(ImageItem(path=path, timer=timer))
                        added = True
        if added:
            self._reapply_timers_if_class()
            self._rebuild()
            self._emit()
        event.acceptProposedAction()
```

Rename to `_handle_external_drop` — keep the body identical.

- [ ] **Step 2: Make `_drop_event` the dispatcher**

Add a new `_drop_event` that dispatches:

```python
    def _drop_event(self, event):
        mime = event.mimeData()
        if mime.hasFormat(TILE_DRAG_MIME):
            self._handle_tile_drop(event)
        elif mime.hasUrls():
            self._handle_external_drop(event)
        else:
            event.ignore()
```

- [ ] **Step 3: Update `_drag_enter` to accept both MIME types**

Find `_drag_enter` (around line 1017). Currently:

```python
    def _drag_enter(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
```

Replace with:

```python
    def _drag_enter(self, event):
        mime = event.mimeData()
        if mime.hasFormat(TILE_DRAG_MIME) or mime.hasUrls():
            event.acceptProposedAction()
```

Also wire `dragMoveEvent` on both scroll areas so insertion-position feedback (added in Task 6) has something to hook. Find the existing scroll-area setup for `_list_scroll` and `_grid_scroll` (around lines 214 and 236) and after `dropEvent = self._drop_event` add:

```python
        self._list_scroll.dragMoveEvent = self._drag_move
        # ...
        self._grid_scroll.dragMoveEvent = self._drag_move
```

Add the handler (can be a stub for now, Task 6 fills in the feedback):

```python
    def _drag_move(self, event):
        mime = event.mimeData()
        if mime.hasFormat(TILE_DRAG_MIME) or mime.hasUrls():
            event.acceptProposedAction()
```

- [ ] **Step 4: Add `_handle_tile_drop` method**

Near `_handle_external_drop`, add:

```python
    def _handle_tile_drop(self, event):
        """Apply an internal tile drop: reorder + pin-flip."""
        try:
            payload = json.loads(
                bytes(event.mimeData().data(TILE_DRAG_MIME)).decode("utf-8")
            )
        except (ValueError, KeyError):
            event.ignore()
            return

        source_indices = payload.get("indices") or []
        if not source_indices:
            event.ignore()
            return

        # Compute insertion index relative to the current tile layout.
        tile_rects = self._compute_tile_rects()
        if tile_rects is None:
            event.ignore()
            return

        # Translate drop position to grid-container coordinates.
        global_pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
        if self._stack.currentWidget() is self._grid_scroll:
            container = self._grid_container
        else:
            container = self._list_container
        container_pos = container.mapFromGlobal(self._grid_scroll.viewport().mapToGlobal(global_pos))
        insert_idx = _compute_insertion_index(
            (container_pos.x(), container_pos.y()), tile_rects,
        )

        # Determine target zone from the neighbors of insert_idx.
        pinned_count = sum(1 for img in self.images if img.pinned)
        target_is_pinned = insert_idx <= pinned_count

        # No-op check: dropping exactly where it was.
        if (len(source_indices) == 1 and
                source_indices[0] == insert_idx - 1 and
                bool(self.images[source_indices[0]].pinned) == target_is_pinned):
            event.acceptProposedAction()
            return

        new_images = _apply_tile_drop(
            self.images, source_indices, insert_idx, target_is_pinned,
        )
        self.images = new_images
        self._rebuild()
        self._emit()
        event.acceptProposedAction()

    def _compute_tile_rects(self):
        """Return a list of (idx, x, y, w, h) for all current tile labels in
        the grid view. Returns None if grid view is not the current widget."""
        if self._stack.currentWidget() is not self._grid_scroll:
            return None
        rects = []
        for _, grid in self._grid_groups:
            for lbl in getattr(grid, "_labels", []):
                idx = lbl.property("img_idx")
                if idx is None:
                    continue
                pos = lbl.pos()
                rects.append((idx, pos.x(), pos.y(), lbl.width(), lbl.height()))
        return rects
```

- [ ] **Step 5: Sanity check + commit**

Run: `python -c "from ui.editor_panel import EditorPanel; print('OK')"` → `OK`.
Run: `python -m pytest -q` → all 174 pass.

```bash
git add ui/editor_panel.py
git commit -m "$(cat <<'EOF'
feat: tile-view drop target dispatches by MIME

Renamed _drop_event to _handle_external_drop (unchanged body) and
made _drop_event a dispatcher that routes on MIME type:
  - application/x-drawer-tile-indices → _handle_tile_drop
  - URL drops                         → _handle_external_drop
_drag_enter accepts both. _handle_tile_drop decodes the JSON payload,
computes the insertion index in the grid coord system, derives the
target zone from the neighbors, and applies _apply_tile_drop +
rebuild + emit change. Same-position no-ops are skipped.

No visual feedback during drag yet — that arrives in the next task.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Tile view drag feedback (floating ghost + source opacity + static gap)

**Files:**
- Modify: `ui/editor_panel.py`

Visual feedback while the drag is in progress: the source tiles go semi-transparent, a tile-sized gap opens at the insertion point (other tiles shift), and a small floating ghost shows the future pin state.

- [ ] **Step 1: Track drag state on EditorPanel**

In `EditorPanel.__init__` (look for `self._selected_tiles = set()`, around line 175), add alongside:

```python
        self._selected_tiles = set()
        # Drag-in-progress state
        self._drag_source_indices = []
        self._drag_insert_idx = None
        self._drag_ghost = None
```

- [ ] **Step 2: Show source-tile opacity + create floating ghost on drag start**

In `_start_tile_drag` (added in Task 4), before `drag.exec(...)`, add:

```python
        # Visual state for drag-in-progress
        self._drag_source_indices = list(source_indices)
        self._apply_source_ghost_opacity(0.35)
        self._drag_ghost = self._build_drag_ghost(source_lbl, source_is_pinned)
```

After `drag.exec(...)` returns (drag finished or cancelled), clean up:

```python
        drag.exec(Qt.DropAction.MoveAction)
        # Cleanup (regardless of drop accept/reject)
        self._apply_source_ghost_opacity(1.0)
        if self._drag_ghost is not None:
            self._drag_ghost.deleteLater()
            self._drag_ghost = None
        self._drag_source_indices = []
        self._drag_insert_idx = None
        # Rebuild to close any gap + restore layout.
        self._rebuild()
```

- [ ] **Step 3: Implement `_apply_source_ghost_opacity` and `_build_drag_ghost`**

Add these helpers near `_start_tile_drag`:

```python
    def _apply_source_ghost_opacity(self, opacity):
        """Set opacity on every tile whose img_idx is in _drag_source_indices."""
        indices = set(self._drag_source_indices)
        for _, grid in self._grid_groups:
            for lbl in getattr(grid, "_labels", []):
                idx = lbl.property("img_idx")
                if idx in indices:
                    effect = lbl.graphicsEffect()
                    from PyQt6.QtWidgets import QGraphicsOpacityEffect
                    if not isinstance(effect, QGraphicsOpacityEffect):
                        effect = QGraphicsOpacityEffect(lbl)
                        lbl.setGraphicsEffect(effect)
                    effect.setOpacity(opacity)

    def _build_drag_ghost(self, source_lbl, source_is_pinned):
        """Create a floating tile-ghost that follows the cursor during drag.
        Its pin icon is shown when the cursor is over the pinned zone."""
        ghost = QLabel(self)
        ghost.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        ghost.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        pix = source_lbl.pixmap()
        if pix and not pix.isNull():
            ghost_pix = pix.scaled(
                pix.width() * 3 // 5, pix.height() * 3 // 5,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            ghost.setPixmap(ghost_pix)
            ghost.setFixedSize(ghost_pix.size())
        ghost._ghost_pinned = source_is_pinned
        ghost.hide()
        return ghost
```

(The ghost stays hidden for now. Task 7 gives it proper positioning during `dragMoveEvent`. The native Qt drag cursor preview set via `drag.setPixmap` already carries a visual; the `_drag_ghost` is a secondary widget we update to show future pin state — but in practice Qt's drag-preview-pixmap + our insertion gap may be enough. If during smoke testing the Qt preview looks fine, we can simplify by dropping the extra ghost in a follow-up.)

- [ ] **Step 4: Gap-during-drag — update `_drag_move` to compute insertion and trigger layout re-run**

Replace the stub `_drag_move` from Task 5 with:

```python
    def _drag_move(self, event):
        mime = event.mimeData()
        if not (mime.hasFormat(TILE_DRAG_MIME) or mime.hasUrls()):
            event.ignore()
            return

        if mime.hasFormat(TILE_DRAG_MIME) and self._stack.currentWidget() is self._grid_scroll:
            # Compute insertion index and trigger gap layout if changed.
            tile_rects = self._compute_tile_rects() or []
            global_pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
            container_pos = self._grid_container.mapFromGlobal(
                self._grid_scroll.viewport().mapToGlobal(global_pos)
            )
            insert_idx = _compute_insertion_index(
                (container_pos.x(), container_pos.y()), tile_rects,
            )
            if insert_idx != self._drag_insert_idx:
                self._drag_insert_idx = insert_idx
                self._relayout_grid_with_gap()
        event.acceptProposedAction()
```

- [ ] **Step 5: Implement `_relayout_grid_with_gap`**

Near `_compute_tile_rects`, add:

```python
    def _relayout_grid_with_gap(self):
        """Re-run the flow layout with a tile-sized virtual slot reserved at
        self._drag_insert_idx. Other tiles shift around the slot."""
        if self._drag_insert_idx is None:
            return
        sz = self._zoom_slider.value()
        for _, grid in self._grid_groups:
            labels = list(getattr(grid, "_labels", []))
            if not labels:
                continue
            w = max(self._grid_scroll.viewport().width(), 200)
            # Insert a virtual None at drag_insert_idx to reserve a slot.
            virtual = labels[:]
            insert_pos = min(self._drag_insert_idx, len(virtual))
            virtual.insert(insert_pos, None)
            _flow_position_with_gaps(virtual, w, sz)
```

- [ ] **Step 6: Add `_flow_position_with_gaps` helper**

Next to the existing `_flow_position` function (around line 124), add a variant that leaves a tile-sized empty slot where a `None` appears in the list:

```python
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

- [ ] **Step 7: Sanity check + commit**

Run: `python -c "from ui.editor_panel import EditorPanel; print('OK')"` → `OK`.
Run: `python -m pytest -q` → all 174 pass.

```bash
git add ui/editor_panel.py
git commit -m "$(cat <<'EOF'
feat: tile-view drag feedback — ghost opacity + static gap

While a tile drag is in progress:
- Source tiles drop to 35% opacity via QGraphicsOpacityEffect.
- A tile-sized virtual slot opens at the current insertion position
  and the surrounding tiles reflow around it (_flow_position_with_gaps
  accepts None entries that reserve a slot without moving any widget).
- _drag_move recomputes the insertion index on every cursor move and
  re-runs the gap layout only when the index changes.

A secondary floating ghost widget is allocated for future pin-state
preview but remains hidden; Qt's own drag-preview pixmap carries the
visible drag cursor for now.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: Tile-view empty-pinned-zone placeholder

**Files:**
- Modify: `ui/editor_panel.py`

When no images are pinned, the tile grid shows a dashed-outline placeholder tile with a centered pin icon as the first slot. Drops on it pin the dropped items.

- [ ] **Step 1: Create a `_PinPlaceholderTile` widget class**

Near `ClickableLabel`, add:

```python
class _PinPlaceholderTile(QLabel):
    """Dashed-outline placeholder for the empty pinned zone.
    Accepts drops (internal tile drags); forwards to EditorPanel._handle_tile_drop."""

    def __init__(self, editor, size, theme, parent=None):
        super().__init__(parent)
        self._editor = editor
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(
            f"border: 2px dashed {theme.text_hint}; "
            f"border-radius: 3px; "
            f"background: transparent;"
        )
        icon_sz = max(16, int(size * 0.35))
        icon = qta.icon(Icons.TOPMOST_ON, color=theme.accent)
        self.setPixmap(icon.pixmap(icon_sz, icon_sz))
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(TILE_DRAG_MIME):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(TILE_DRAG_MIME):
            event.acceptProposedAction()

    def dropEvent(self, event):
        """Drop on placeholder = pin at index 0."""
        try:
            payload = json.loads(
                bytes(event.mimeData().data(TILE_DRAG_MIME)).decode("utf-8")
            )
        except (ValueError, KeyError):
            event.ignore()
            return
        source_indices = payload.get("indices") or []
        if not source_indices:
            event.ignore()
            return
        new_images = _apply_tile_drop(
            self._editor.images, source_indices, insert_idx=0,
            target_is_pinned=True,
        )
        self._editor.images = new_images
        self._editor._rebuild()
        self._editor._emit()
        event.acceptProposedAction()
```

- [ ] **Step 2: Render placeholder in `_rebuild_grid`**

Find `_rebuild_grid` (around line 579). Locate the loop over `ordered` that builds `header + grid + labels`. Before the main loop, count pinned:

```python
        pinned_count = sum(1 for img in self.images if img.pinned)
```

Inside the loop, at the very first group (quick mode has one group), conditionally prepend a placeholder widget to the labels list:

Find this section (around line 610):

```python
            grid = QWidget(self._grid_container)
            labels = []
            for idx, img in items:
                ...
```

Change to:

```python
            grid = QWidget(self._grid_container)
            labels = []
            # Empty pinned zone → placeholder as first tile (quick mode only).
            if (self._timer_mode == "quick" and pinned_count == 0
                    and not labels):
                placeholder = _PinPlaceholderTile(
                    editor=self, size=sz, theme=t, parent=grid,
                )
                labels.append(placeholder)
            for idx, img in items:
                ...
```

The placeholder shares the `labels` list so `_flow_position(labels, w, sz)` at the end naturally lays it out. Note that `_flow_position` treats everything as a widget with `pixmap()` + size — the placeholder's `setPixmap(icon.pixmap(...))` returns a valid pixmap so the flow layout will size it as `icon_sz × icon_sz`. That's smaller than a tile. To make the placeholder full-tile-sized, override `pixmap()` behavior or set a size hint.

Simpler fix — inside `_flow_position`, the code checks `if pix and not pix.isNull()` and uses `pix.width(), pix.height()` for sizing. The placeholder's pixmap is `icon_sz × icon_sz` (smaller). To force full tile size, either:
  a) Set no pixmap on the placeholder (leave it unset), which makes `_flow_position` fall back to `w, h = sz, sz`. But then the icon won't show.
  b) Make the placeholder use a custom-composed pixmap that is `sz × sz` total with the icon centered inside.

Go with (b). Update `_PinPlaceholderTile` to build a `sz × sz` pixmap with the icon centered:

```python
class _PinPlaceholderTile(QLabel):
    def __init__(self, editor, size, theme, parent=None):
        super().__init__(parent)
        self._editor = editor
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(
            f"border: 2px dashed {theme.text_hint}; "
            f"border-radius: 3px; "
            f"background: transparent;"
        )
        # Build a tile-sized transparent pixmap with the pin icon centered.
        from PyQt6.QtGui import QPixmap
        pix = QPixmap(size, size)
        pix.fill(QColor(0, 0, 0, 0))
        icon_sz = max(16, int(size * 0.35))
        icon = qta.icon(Icons.TOPMOST_ON, color=theme.accent)
        icon_pix = icon.pixmap(icon_sz, icon_sz)
        p = QPainter(pix)
        p.drawPixmap(
            (size - icon_sz) // 2,
            (size - icon_sz) // 2,
            icon_pix,
        )
        p.end()
        self.setPixmap(pix)
        self.setAcceptDrops(True)
    # ... (dragEnterEvent, dragMoveEvent, dropEvent same as before)
```

- [ ] **Step 3: Skip placeholder in `_on_reorder` / selection / delete**

The placeholder has no `img_idx` property set. Code that uses `lbl.property("img_idx")` already returns `None` for it. Double-check the delete path (around `_delete_selected` near line 949) — verify it filters on `idx is not None` before adding to removal set. It does (existing code):

```python
        for lbl in self._selected_tiles:
            idx = lbl.property("img_idx")
            if idx is not None:
                indices_to_remove.add(idx)
```

Safe. No change needed there.

- [ ] **Step 4: Sanity check + commit**

Run: `python -c "from ui.editor_panel import EditorPanel, _PinPlaceholderTile; print('OK')"` → `OK`.
Run: `python -m pytest -q` → all 174 pass.

```bash
git add ui/editor_panel.py
git commit -m "$(cat <<'EOF'
feat: empty pinned-zone placeholder tile (tile view)

When pinned_count == 0 in quick-mode tile view, prepend a
dashed-outline _PinPlaceholderTile as the first grid slot. The
placeholder renders a tile-sized transparent pixmap with the pin
icon centered; accepts drops of our internal MIME; on drop, pins the
dropped items at index 0. Disappears on the next _rebuild once a tile
is pinned.

No img_idx on the placeholder so select/delete paths skip it
naturally.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: List-view quick-mode custom drop + placeholder row

**Files:**
- Modify: `ui/editor_panel.py`

List view in quick mode already had `InternalMove`. Now it must:
- Enforce cross-zone pin flip on drops between zones.
- Render a "drop here to pin" placeholder widget above the list when `pinned_count == 0`.

The list view has one `QListWidget` per tier; in quick mode this is one widget.

- [ ] **Step 1: Monkey-patch `dropEvent` on each quick-mode `QListWidget`**

In `_rebuild_list`, after the existing `lw.setDragDropMode(...)` branching from Task 2, wire a custom `dropEvent` for quick-mode list widgets.

Find (around line 528-533 after Task 2's edits):

```python
            if self._timer_mode == "quick":
                lw.setDragDropMode(QListWidget.DragDropMode.InternalMove)
            else:
                lw.setDragDropMode(QListWidget.DragDropMode.NoDragDrop)
            lw.setDefaultDropAction(Qt.DropAction.MoveAction)
            lw.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
            lw.setIconSize(QSize(24, 24))
            lw.setStyleSheet(self._list_style)
            lw.model().rowsMoved.connect(self._on_reorder)
```

Replace with:

```python
            if self._timer_mode == "quick":
                lw.setDragDropMode(QListWidget.DragDropMode.InternalMove)
            else:
                lw.setDragDropMode(QListWidget.DragDropMode.NoDragDrop)
            lw.setDefaultDropAction(Qt.DropAction.MoveAction)
            lw.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
            lw.setIconSize(QSize(24, 24))
            lw.setStyleSheet(self._list_style)
            lw.model().rowsMoved.connect(self._on_reorder)

            if self._timer_mode == "quick":
                self._install_list_drop_handler(lw)
```

Add the helper:

```python
    def _install_list_drop_handler(self, lw):
        """Wrap the QListWidget's dropEvent with cross-zone pin-flip logic."""
        editor = self
        original_drop = lw.dropEvent

        def _drop(event):
            # Capture source rows (selected rows before the move) and their
            # img_idx (UserRole). Determine target row from event position.
            source_rows = sorted(r.row() for r in lw.selectedIndexes())
            source_indices = []
            for row in source_rows:
                item = lw.item(row)
                idx = item.data(Qt.ItemDataRole.UserRole)
                if idx is not None and idx < len(editor.images):
                    source_indices.append(idx)

            target_row = lw.indexAt(event.position().toPoint()).row()
            if target_row < 0:
                target_row = lw.count()

            # Determine target zone from the neighbor rows.
            # target_row is the row where the drop lands; rows before it stay.
            pinned_count = sum(1 for img in editor.images if img.pinned)
            target_is_pinned = target_row <= pinned_count

            # Filter source_indices to same zone as the first source item —
            # Qt allows multi-row drags across zones, but spec says filter.
            if source_indices:
                first_is_pinned = bool(editor.images[source_indices[0]].pinned)
                source_indices = _filter_selection_by_zone(
                    source_indices, first_is_pinned, editor.images,
                )

            if not source_indices:
                event.ignore()
                return

            new_images = _apply_tile_drop(
                editor.images, source_indices, target_row, target_is_pinned,
            )
            editor.images = new_images
            editor._rebuild()
            editor._emit()
            event.acceptProposedAction()

        lw.dropEvent = _drop
```

- [ ] **Step 2: Render list-view placeholder when empty pinned zone**

At the start of `_rebuild_list`, before the loop that creates per-tier widgets, count pinned:

```python
        pinned_count = sum(1 for img in self.images if img.pinned)
```

When `self._timer_mode == "quick"` and `pinned_count == 0`, insert a placeholder widget as the first widget in `self._list_layout`. Create a `_PinPlaceholderRow` class:

```python
class _PinPlaceholderRow(QLabel):
    """A dashed-outline 'drop here to pin' row for the empty pinned zone in
    quick-mode list view."""

    def __init__(self, editor, theme, parent=None):
        super().__init__(parent)
        self._editor = editor
        self.setText("  drop here to pin  ")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(S.LIST_ITEM_H)
        self.setStyleSheet(
            f"border: 2px dashed {theme.text_hint}; "
            f"border-radius: 3px; "
            f"color: {theme.text_hint}; "
            f"font-size: {S.FONT_BUTTON}px; "
            f"background: transparent;"
        )
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(TILE_DRAG_MIME):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(TILE_DRAG_MIME):
            event.acceptProposedAction()

    def dropEvent(self, event):
        try:
            payload = json.loads(
                bytes(event.mimeData().data(TILE_DRAG_MIME)).decode("utf-8")
            )
        except (ValueError, KeyError):
            event.ignore()
            return
        source_indices = payload.get("indices") or []
        if not source_indices:
            event.ignore()
            return
        new_images = _apply_tile_drop(
            self._editor.images, source_indices, insert_idx=0,
            target_is_pinned=True,
        )
        self._editor.images = new_images
        self._editor._rebuild()
        self._editor._emit()
        event.acceptProposedAction()
```

Place this class definition near `_PinPlaceholderTile`.

In `_rebuild_list`, after `self._list_layout` is cleared (existing logic), and before inserting tier groups, insert the placeholder row when needed. Find `_rebuild_list` entry point (around line 497). After the layout-clearing loop but before the per-tier loop, add:

```python
        pinned_count = sum(1 for img in self.images if img.pinned)
        if self._timer_mode == "quick" and pinned_count == 0:
            placeholder = _PinPlaceholderRow(editor=self, theme=self.theme)
            self._list_layout.insertWidget(0, placeholder)
            self._list_placeholder_row = placeholder
            insert_pos = 1
        else:
            self._list_placeholder_row = None
            insert_pos = 0
```

Where `insert_pos` is the starting position for inserting the tier widgets (preserving the stretch at the end). Adjust the existing tier loop to use `insert_pos` as the starting position (if it currently uses hardcoded `0` or similar).

(The existing `_rebuild_list` loop likely already maintains an `insert_pos` counter. If so, initialize it from the calculated `insert_pos` above instead of 0.)

- [ ] **Step 3: Drag source for list-view rows (quick mode)**

Qt's `InternalMove` DragDropMode handles the drag-source side of list items automatically (row becomes draggable by default when `InternalMove` is active). No additional code needed. The custom dropEvent we installed handles the drop side.

- [ ] **Step 4: Sanity check + commit**

Run: `python -c "from ui.editor_panel import EditorPanel, _PinPlaceholderRow; print('OK')"` → `OK`.
Run: `python -m pytest -q` → all 174 pass.

```bash
git add ui/editor_panel.py
git commit -m "$(cat <<'EOF'
feat: list-view cross-zone drops + empty-pinned placeholder row

Quick-mode list widgets get a custom dropEvent wrapper that reads
the selected source rows, computes the target row + target zone,
filters the selection to same-zone members, applies _apply_tile_drop
for reorder + pin flip, then rebuilds.

When pinned_count == 0 in quick-mode list view, a _PinPlaceholderRow
is prepended above the first tier widget. Dashed border, centered
'drop here to pin' label, accepts TILE_DRAG_MIME drops and pins at
index 0.

Class mode keeps the NoDragDrop setting from Task 2.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 9: Manual smoke test (for Oksana)

**Files:** none — user verification only.

Runs after all prior tasks merge and the branch is pushed.

- [ ] **Step 1: Launch the app**

Run: `python main.py`
Load a session with 15+ images.

- [ ] **Step 2: Quick mode, tile view — empty pinned zone + first pin**

1. Switch to quick mode, tile view. Make sure no images are pinned yet.
2. Verify the dashed "pin here" placeholder tile appears as the first tile.
3. Drag a non-pinned tile onto the placeholder. Drop.
4. Verify the dragged tile becomes pinned (accent pin icon appears), placeholder disappears.

- [ ] **Step 3: Pin more + reorder within zone**

1. Drag another non-pinned tile up past the first pinned tile. Drop.
2. Verify it joins the pinned row.
3. Drag a pinned tile to reorder within the pinned zone. Start a session — verify the first image shown is now the leftmost pinned tile.

- [ ] **Step 4: Unpin by cross-zone drag**

1. Drag a pinned tile down past the last pinned position into the non-pinned area. Drop.
2. Verify it unpins (pin icon disappears).
3. If this was the last pinned tile, verify the dashed placeholder reappears.

- [ ] **Step 5: Multi-select drag with mixed zones**

1. Pin 2 tiles. Select 3 tiles total — 2 pinned + 1 non-pinned — with Ctrl-click.
2. Drag one of the pinned tiles. Verify only the 2 pinned selection members move; the non-pinned selection member stays put.

- [ ] **Step 6: External file drop still works**

1. Drag files from Windows Explorer onto the tile grid. Verify new images are added (existing flow unchanged).

- [ ] **Step 7: Drop outside grid**

1. Drag a tile and release outside the editor window. Verify no change.

- [ ] **Step 8: Class mode — no drag**

1. Switch to class mode.
2. Attempt to drag a tile. Verify drag cannot start.
3. Switch to list view. Attempt to drag a list row. Verify drag cannot start.

- [ ] **Step 9: List view quick mode — empty-pinned placeholder**

1. Switch back to quick mode, list view. Verify no pinned images → the "drop here to pin" dashed row appears above the list.
2. Drag an item onto the dashed row. Verify it becomes pinned, placeholder disappears.

- [ ] **Step 10: Selection clears on empty click**

1. Click an image to select (accent frame appears).
2. Click empty grid/list space. Verify selection clears (frame disappears).

- [ ] **Step 11: Selection frame corners + pin icon color**

1. Select a tile. Verify the selection frame has rounded corners matching the tile's rounded corners.
2. Verify the tile-view pin icon uses the theme accent color (same as list-view pinned-entry color).

- [ ] **Step 12: Report**

If all steps pass, report "looks good." Otherwise describe what broke (screenshots welcome).

---

## Self-review summary

- **Spec coverage:**
  - Tile-view drag-drop (insertion, zone rules) → Tasks 4–6
  - Cross-zone pin flip (bulk pin/unpin) → Task 1 (`_apply_tile_drop`) + Task 5 (wiring)
  - Multi-select drag with zone filter → Task 1 (`_filter_selection_by_zone`) + Task 4 (drag source)
  - Source ghost opacity + static gap → Task 6
  - Empty pinned zone placeholder (tile + list) → Tasks 7 and 8
  - Class mode no drag (tile + list) → Task 2 (list) + Task 4 (tile guard `_timer_mode == "quick"`)
  - Selection clears on empty-area click → Task 3
  - Selection frame rounded corners → Task 2
  - Pin icon color fix → Task 2
  - External file drop unchanged → Task 5 (`_drop_event` dispatcher)
  - List-view quick-mode custom drop with pin flip → Task 8

- **Placeholders:** none. Every step has executable code and exact commands.

- **Type consistency:** `TILE_DRAG_MIME` used consistently across all tasks. Helper names (`_compute_insertion_index`, `_filter_selection_by_zone`, `_apply_tile_drop`) stay identical from Task 1 through downstream callers. Payload schema (`{"indices": [...], "source_is_pinned": bool}`) is consistent between drag-source (Task 4) and drop-target (Tasks 5, 7, 8).

- **Out of scope:**
  - Animated tile reorder — deferred, memory `project_animated_reorder.md`.
  - Rubber-band selection — future spec.
  - Drag to external apps — not supported.
  - Shuffle coupling between modes — deferred, memory `project_shuffle_coupling.md`.
  - Tier migration bug — separate memory, not addressed here.
