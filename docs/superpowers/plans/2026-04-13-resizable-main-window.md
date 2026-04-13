# Resizable Main Window Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the main window resizable as a square, where the window size controls the UI scale — bigger window = bigger fonts, icons, and spacing everywhere.

**Architecture:** Replace `setFixedSize` with `setMinimumSize` + square aspect ratio constraint. On resize release, compute `user_factor = window_size / 250`, multiply with DPI factor, call `init_scale()`, and rebuild both settings and editor UIs. Persist size in session JSON.

**Tech Stack:** PyQt6, existing `ui/scales.py` scaling system

---

### Task 1: Modify init_scale to support combined DPI + user factor

**Files:**
- Modify: `ui/scales.py:15-20`
- Modify: `main.py:73`
- Test: `tests/test_scales.py`

- [ ] **Step 1: Write failing test for combined scale**

Add to `tests/test_scales.py`:

```python
def test_init_scale_combined_factors():
    """init_scale accepts dpi_factor and user_factor separately."""
    init_scale(2.0, user_factor=1.2)
    # effective = 2.0 * 1.2 = 2.4
    assert S.MAIN_W == round(250 * 2.4)  # 600
    assert S.MARGIN == round(14 * 2.4)   # 34
    init_scale(1.0)


def test_init_scale_user_factor_only():
    """User factor alone works (DPI defaults to stored value)."""
    init_scale(1.0)  # set DPI baseline
    from ui.scales import rescale_user
    rescale_user(1.5)
    assert S.MAIN_W == round(250 * 1.5)  # 375
    assert S.MARGIN == round(14 * 1.5)   # 21
    rescale_user(1.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_scales.py::test_init_scale_combined_factors -v`
Expected: FAIL — `init_scale` doesn't accept `user_factor`

- [ ] **Step 3: Implement combined scaling in scales.py**

Modify `ui/scales.py` — replace the `init_scale` function and add `rescale_user`:

```python
_dpi_factor = 1.0
_user_factor = 1.0

def init_scale(dpi_factor, user_factor=1.0):
    """Set DPI and user scale factors. Recomputes all S.* constants."""
    global _factor, _dpi_factor, _user_factor
    _dpi_factor = dpi_factor
    _user_factor = user_factor
    _factor = dpi_factor * user_factor
    for attr, val in _BASE.items():
        setattr(S, attr, round(val * _factor))

def rescale_user(user_factor):
    """Change user scale factor only, keeping DPI factor."""
    init_scale(_dpi_factor, user_factor)
```

- [ ] **Step 4: Update main.py to pass dpi_factor explicitly**

In `main.py:73`, change:
```python
init_scale(factor)
```
to:
```python
init_scale(factor, user_factor=1.0)
```

- [ ] **Step 5: Run all scale tests**

Run: `python -m pytest tests/test_scales.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add ui/scales.py main.py tests/test_scales.py
git commit -m "feat: add combined DPI + user scale factor to init_scale"
```

---

### Task 2: Add resize handling to settings window

**Files:**
- Modify: `ui/settings_window.py:54-57` (window setup)
- Modify: `ui/settings_window.py:252-261` (mouse events)

- [ ] **Step 1: Remove setFixedSize, add setMinimumSize**

In `ui/settings_window.py`, replace line 57:
```python
self.setFixedSize(S.MAIN_W, S.MAIN_H)
```
with:
```python
self.setMinimumSize(200, 200)
self.resize(S.MAIN_W, S.MAIN_H)
self._resizing = False
self._resize_edge = None
self._resize_start = None
self._resize_geo = None
self._last_edge = None
```

- [ ] **Step 2: Add edge detection and cursor methods**

Add to `SettingsWindow` class, before the mouse event methods:

```python
def _edge_at(self, pos, cursor_only=False):
    """Return which edge(s) the cursor is near, or None."""
    r = self.rect()
    e = S.RESIZE_CURSOR_W if cursor_only else S.RESIZE_GRIP_W
    edges = ""
    if pos.y() < e:
        edges += "t"
    elif pos.y() > r.height() - e:
        edges += "b"
    if pos.x() < e:
        edges += "l"
    elif pos.x() > r.width() - e:
        edges += "r"
    return edges or None

def _cursor_for_edge(self, edge):
    if edge in ("tl", "br"):
        return Qt.CursorShape.SizeFDiagCursor
    if edge in ("tr", "bl"):
        return Qt.CursorShape.SizeBDiagCursor
    if edge in ("t", "b", "l", "r"):
        return Qt.CursorShape.SizeFDiagCursor  # square = always diagonal
    return Qt.CursorShape.ArrowCursor
```

- [ ] **Step 3: Update mouse event methods**

Replace `mousePressEvent`, `mouseMoveEvent`, `mouseReleaseEvent`:

```python
def mousePressEvent(self, event):
    if event.button() == Qt.MouseButton.LeftButton:
        edge = self._edge_at(event.pos())
        if edge:
            self._resizing = True
            self._resize_edge = edge
            self._resize_start = event.globalPosition().toPoint()
            self._resize_geo = self.geometry()
            event.accept()
            return
    self._resizing = False
    self.snap_mouse_press(event)

def mouseMoveEvent(self, event):
    if not event.buttons():
        edge = self._edge_at(event.pos(), cursor_only=True)
        if edge != self._last_edge:
            self._last_edge = edge
            self.setCursor(self._cursor_for_edge(edge) if edge else Qt.CursorShape.ArrowCursor)
        return
    if self._resizing and self._resize_edge:
        delta = event.globalPosition().toPoint() - self._resize_start
        geo = self._resize_geo
        # Use max delta for square constraint
        dx = delta.x() if "r" in self._resize_edge else -delta.x()
        dy = delta.y() if "b" in self._resize_edge else -delta.y()
        d = max(dx, dy)
        new_size = max(200, geo.width() + d)
        from PyQt6.QtCore import QRect
        new_geo = QRect(geo)
        # Grow from the appropriate corner/edge
        if "r" in self._resize_edge or (self._resize_edge in ("t", "b")):
            new_geo.setRight(geo.left() + new_size - 1)
        if "l" in self._resize_edge:
            new_geo.setLeft(geo.right() - new_size + 1)
        if "b" in self._resize_edge or (self._resize_edge in ("l", "r")):
            new_geo.setBottom(geo.top() + new_size - 1)
        if "t" in self._resize_edge:
            new_geo.setTop(geo.bottom() - new_size + 1)
        self.setGeometry(new_geo)
        event.accept()
        return
    self.snap_mouse_move(event)

def mouseReleaseEvent(self, event):
    if self._resizing:
        self._resizing = False
        self._resize_edge = None
        self._apply_user_scale()
        return
    self.snap_mouse_release(event)
```

- [ ] **Step 4: Run all tests**

Run: `python -m pytest tests/ -x -q`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add ui/settings_window.py
git commit -m "feat: make settings window resizable as square"
```

---

### Task 3: Apply scale on resize release

**Files:**
- Modify: `ui/settings_window.py`

- [ ] **Step 1: Add _apply_user_scale method**

Add to `SettingsWindow`:

```python
def _apply_user_scale(self):
    """Recalculate UI scale from current window size and rebuild."""
    from ui.scales import rescale_user, _BASE
    base_size = _BASE["MAIN_W"]  # 250
    user_factor = self.width() / base_size
    rescale_user(user_factor)

    # Rebuild this window's UI
    self._apply_theme()
    self._timer_panel.apply_theme()
    self._bottom_bar.apply_theme()
    self.centralWidget().layout().setContentsMargins(
        S.MARGIN, S.MARGIN_TOP, S.MARGIN, S.MARGIN_BOTTOM)
    self._panel.setStyleSheet("")  # force re-layout
    self._panel._radius = S.PANEL_RADIUS
    self._panel.update()

    # Rebuild editor if open
    if self._editor_visible:
        self.editor.resize(S.EDITOR_W, self.height())
        self.editor._apply_theme()
        self.editor._panel.theme = self.theme
        self.editor._panel._apply_theme()
        self.editor._panel._rebuild()
        if self._snapped_children:
            self._move_children()
```

- [ ] **Step 2: Run app manually to verify resize works**

Run: `python main.py`
- Drag a corner of the settings window to resize
- Verify it stays square
- Verify UI elements scale on release

- [ ] **Step 3: Run all tests**

Run: `python -m pytest tests/ -x -q`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add ui/settings_window.py
git commit -m "feat: apply UI scale on resize release, rebuild both windows"
```

---

### Task 4: Persist window size in session

**Files:**
- Modify: `ui/settings_window.py:534-555` (save/restore)
- Modify: `main.py:59-79` (load size before building UI)
- Test: `tests/test_scales.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_scales.py`:

```python
def test_user_factor_from_saved_size():
    """Saved window size 300 with base 250 gives user_factor 1.2."""
    init_scale(1.0, user_factor=300 / 250)
    assert S.MAIN_W == round(250 * 1.2)  # 300
    init_scale(1.0)
```

- [ ] **Step 2: Run test to verify it fails or passes**

Run: `python -m pytest tests/test_scales.py::test_user_factor_from_saved_size -v`

- [ ] **Step 3: Add window_size to _save_session**

In `ui/settings_window.py`, in `_save_session()`, add to the data dict:

```python
"window_size": self.width(),
```

- [ ] **Step 4: Load window_size in main.py before building UI**

Modify `main.py` — after `init_scale(factor)` and before `window = SettingsWindow()`:

```python
# Load saved window size for user scale
from core.session import load_session
from ui.scales import rescale_user, _BASE
saved = load_session()
if saved and "window_size" in saved:
    user_factor = saved["window_size"] / _BASE["MAIN_W"]
    rescale_user(user_factor)
```

- [ ] **Step 5: Restore window size in _restore_session**

In `ui/settings_window.py`, in `_restore_session()`, add after loading other state:

```python
saved_size = data.get("window_size")
if saved_size:
    self.resize(saved_size, saved_size)
```

- [ ] **Step 6: Run all tests**

Run: `python -m pytest tests/ -x -q`
Expected: All PASS

- [ ] **Step 7: Commit**

```bash
git add ui/settings_window.py main.py tests/test_scales.py
git commit -m "feat: persist window size in session, restore scale on launch"
```

---

### Task 5: Move snapped children after resize

**Files:**
- Modify: `ui/settings_window.py`

- [ ] **Step 1: Update _apply_user_scale to reposition snapped editor**

In the `_apply_user_scale` method, ensure snapped children are repositioned after the main window resizes. The `_move_children()` call already added in Task 3 handles this, but we also need to update the snap position calculation since the main window geometry changed.

After `self.editor.resize(...)` in `_apply_user_scale`, add:

```python
# Reposition snapped editor to align with new window size
if self.editor._snapped_to is not None:
    snap_pos = self.editor._calc_snap_pos(self, "right")
    if snap_pos:
        self.editor.move(snap_pos)
self.update()
self.editor.update()
```

- [ ] **Step 2: Run app manually**

Run: `python main.py`
- Open editor, snap it to main window
- Resize main window
- Verify editor moves correctly and scales

- [ ] **Step 3: Run all tests**

Run: `python -m pytest tests/ -x -q`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add ui/settings_window.py
git commit -m "fix: reposition snapped editor after resize scale change"
```

---

### Task 6: Final integration test and cleanup

**Files:**
- Test: manual testing
- Modify: any files needing adjustment

- [ ] **Step 1: Test resize at various sizes**

Run: `python main.py`
Test these scenarios:
- Resize to minimum (200px) — UI should be readable
- Resize to ~400px — UI should scale up proportionally
- Open editor while resized — editor matches scale
- Close and reopen app — size and scale are remembered
- Resize with editor snapped — editor follows and rescales

- [ ] **Step 2: Run full test suite**

Run: `python -m pytest tests/ -x -q`
Expected: All 150+ PASS

- [ ] **Step 3: Final commit if any fixes were needed**

```bash
git add -A
git commit -m "fix: integration fixes for resizable main window"
```
