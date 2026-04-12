# DPI-Aware Scaling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the app scale proportionally to screen resolution so it looks correct on 1080p, QHD, 4K, and macOS Retina displays.

**Architecture:** Detect screen logical height at startup, compute a scale factor relative to 1080p, and multiply all pixel dimensions in `scales.py` by that factor. Existing code reads `S.MARGIN` etc. as before — values are pre-scaled. Hardcoded pixel values scattered across 12 files get centralized into `scales.py` first.

**Tech Stack:** PyQt6, `QScreen.availableSize()` for detection

**Spec:** `docs/superpowers/specs/2026-04-12-dpi-aware-scaling-design.md`

---

### Task 1: Add scaling infrastructure to scales.py

**Files:**
- Modify: `ui/scales.py`
- Modify: `tests/test_scales.py`

- [ ] **Step 1: Write failing tests for sc() and init_scale()**

Add to `tests/test_scales.py`:

```python
from ui.scales import sc, init_scale


def test_sc_default_factor():
    """At default factor 1.0, sc() returns the input unchanged."""
    assert sc(14) == 14
    assert sc(250) == 250
    assert sc(7) == 7


def test_sc_rounds_to_int():
    """sc() returns an integer."""
    assert isinstance(sc(14), int)


def test_init_scale_multiplies_values():
    """After init_scale(2.0), all S.* pixel constants are doubled."""
    init_scale(2.0)
    assert S.MAIN_W == 500
    assert S.MAIN_H == 500
    assert S.MARGIN == 28
    assert S.FONT_TITLE == 34
    assert S.ICON_START == 104
    # Ratios should NOT change
    assert S.START_ICON_RATIO == 0.75
    assert S.START_RADIUS_RATIO == 0.19
    # Reset to default
    init_scale(1.0)


def test_init_scale_reset():
    """init_scale(1.0) restores base values."""
    init_scale(2.0)
    init_scale(1.0)
    assert S.MAIN_W == 250
    assert S.MARGIN == 14
    assert S.FONT_TITLE == 17


def test_sc_uses_current_factor():
    """sc() reflects the most recent init_scale() call."""
    init_scale(1.5)
    assert sc(100) == 150
    assert sc(7) == 10  # round(7 * 1.5) = 10.5 -> 10
    init_scale(1.0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_scales.py -v`
Expected: FAIL — `sc` and `init_scale` not importable

- [ ] **Step 3: Implement sc() and init_scale() in scales.py**

Replace the entire `ui/scales.py` with:

```python
# ui/scales.py
"""Centralized size definitions — single source of truth for all UI dimensions."""

_factor = 1.0

# Base values (unscaled) — used by init_scale to recompute S.* constants
_BASE = {}


def sc(value):
    """Scale a pixel value by the current factor, rounded to int."""
    return round(value * _factor)


def init_scale(factor):
    """Recompute all S.* pixel constants with the given factor. Call once at startup."""
    global _factor
    _factor = factor
    for attr, val in _BASE.items():
        setattr(S, attr, round(val * factor))


class _SMeta(type):
    """Metaclass that records base values of int/float class attributes."""
    def __init__(cls, name, bases, namespace):
        super().__init__(name, bases, namespace)
        for attr, val in namespace.items():
            if attr.startswith('_'):
                continue
            if isinstance(val, int):
                _BASE[attr] = val
            # floats (ratios) are NOT recorded — they don't scale


class S(metaclass=_SMeta):
    # Window
    MAIN_W = 250
    MAIN_H = 250
    EDITOR_W = 250
    WINDOW_RADIUS = 8

    # Margins
    MARGIN = 14
    MARGIN_TOP = 12
    MARGIN_BOTTOM = 14

    # Icons — header row
    ICON_HEADER = 13
    ACCENT_DOT = 11

    # Icons — bottom bar
    ICON_START = 52

    # Start button (ratios — NOT scaled)
    START_ICON_RATIO = 0.75
    START_RADIUS_RATIO = 0.19  # ~10px on 52px button

    # Title
    TITLE_W = 105
    TITLE_Y_NUDGE = 4

    # Fonts (px)
    FONT_TITLE = 17
    FONT_BUTTON = 11
    FONT_MODE = 11
    FONT_LABEL = 9
    FONT_HINT = 10
    FONT_TOTAL = 13

    # Spacing
    SPACING_HEADER = 6
    SPACING_MODE = 6
    SPACING_TIERS = 4
    SPACING_SUMMARY = 6

    # Timer buttons
    TIMER_BTN_PADDING_V = 7
    TIMER_BTN_PADDING_H = 7
    TIMER_BTN_RADIUS = 5
    MODE_BTN_RADIUS = 5
    PANEL_RADIUS = 6
    PANEL_PADDING = 6

    # Editor
    EDITOR_BTN = 15
    EDITOR_BTN_BOTTOM = 11
```

The metaclass `_SMeta` automatically records every `int` class attribute into `_BASE` at class creation time. Ratios are `float` and excluded. `init_scale()` iterates `_BASE` and overwrites each attribute with `round(base * factor)`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_scales.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add ui/scales.py tests/test_scales.py
git commit -m "feat: add sc() and init_scale() for DPI-aware scaling"
```

---

### Task 2: Add new constants to scales.py for all hardcoded values

**Files:**
- Modify: `ui/scales.py`

- [ ] **Step 1: Add all new constants to S class**

Add the following groups to `ui/scales.py` inside class `S`, after the existing constants:

```python
    # Viewer window
    VIEWER_MIN_W = 200
    VIEWER_MIN_H = 150
    VIEWER_CORNER_GRIP = 50
    VIEWER_NAV_ZONE = 40
    VIEWER_CENTER_BTN = 60
    VIEWER_ICON_LABEL = 20
    VIEWER_ICON_BTN = 26
    VIEWER_ICON_MARGIN = 8
    VIEWER_ICON_GAP = 4
    VIEWER_PROGRESS_H = 3
    VIEWER_BOTTOM_LABEL_H = 24
    VIEWER_BOTTOM_OFFSET = 8
    VIEWER_BOTTOM_LABEL_X = 10
    VIEWER_BOTTOM_ICON_SPACING = 26
    VIEWER_BOTTOM_ICON_Y_OFFSET = 2
    VIEWER_LEFT_NAV_X = 4
    VIEWER_LEFT_NAV_W = 25
    VIEWER_LEFT_NAV_H = 40
    VIEWER_HELP_MARGIN = 20

    # Viewer fonts (px)
    FONT_TIMER = 20
    FONT_COUNTER = 13
    FONT_HELP = 14

    # Scrollbar
    SCROLLBAR_W = 4
    SCROLLBAR_HANDLE_MIN_H = 20
    SCROLLBAR_RADIUS = 2

    # Editor panel
    GRID_MIN = 48
    GRID_MAX = 256
    GRID_DEFAULT = 80
    GRID_ZOOM_STEP = 16
    GRID_TILE_RADIUS = 3
    GRID_SPACING = 4
    COLOR_LINE_H = 1
    ZOOM_SLIDER_W = 90
    LIST_ITEM_H = 30
    LIST_ITEM_PADDING = 2
    LIST_PADDING = 4
    LIST_SPACING = 4
    HEADER_PADDING_TOP = 3
    HEADER_PADDING_H = 2
    HEADER_PADDING_BOTTOM = 1
    SLIDER_GROOVE_H = 4
    SLIDER_HANDLE_W = 12
    SLIDER_HANDLE_MARGIN = 4
    PIN_OVERLAY_PADDING = 2
    PIN_POS_X_OFFSET = 4
    PIN_POS_Y_OFFSET = 2
    FONT_MSG_BOX = 12
    EDITOR_BORDER_SELECTED = 2
    EDITOR_BORDER_DASHED = 1

    # Accent picker
    ACCENT_SQ = 120
    ACCENT_BAR_W = 12
    ACCENT_MARGIN = 10
    ACCENT_SPACING = 8
    ACCENT_ROW_SPACING = 6
    ACCENT_HEX_H = 20
    ACCENT_HEX_RADIUS = 2
    ACCENT_HEX_FONT = 10
    ACCENT_OFFSET_Y = 4

    # Timer panel
    TIMER_MODE_BTN_H = 28
    MODE_BTN_PADDING_V = 4
    MODE_BTN_PADDING_H = 8

    # Image editor window
    RESIZE_GRIP_W = 6
    EDITOR_TITLE_SPACING = 4
    EDITOR_TITLE_BOTTOM_SPACE = 6
    EDITOR_MIN_W = 200
    EDITOR_MIN_H = 200
    EDGE_SNAP_THRESHOLD = 12

    # Snap
    SNAP_DISTANCE = 15
    DETACH_DISTANCE = 40

    # Bottom bar
    SUMMARY_TIME_SPACING = 4
    START_BTN_SPACING = 8
    FONT_LIMIT_BTN = 9
    FONT_LIMIT_SEP = 10

    # URL dialog
    URL_DLG_MIN_W = 400
    URL_DLG_MARGIN_H = 16
    URL_DLG_MARGIN_V = 12
    URL_DLG_SPACING = 8
    URL_ROW_SPACING = 6
    URL_FILE_LIST_MIN_H = 200
    URL_PREVIEW_SIZE = 48
    URL_INPUT_PADDING = 6
    URL_INPUT_FONT = 11
    URL_BTN_FONT = 10
    URL_BTN_PADDING_V = 3
    URL_BTN_PADDING_H = 6
    URL_LIST_ITEM_PADDING = 3
    URL_PROGRESS_H = 8

    # Widgets / misc
    TEXT_SHADOW_OFFSET = 1
    BORDER_WIDTH = 1
```

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests/ -x -q`
Expected: ALL PASS (new constants don't break anything)

- [ ] **Step 3: Commit**

```bash
git add ui/scales.py
git commit -m "feat: add 70+ new constants to scales.py for DPI centralization"
```

---

### Task 3: Update main.py startup sequence

**Files:**
- Modify: `main.py`
- Test: `tests/test_scales.py`

- [ ] **Step 1: Write failing test for detect_scale_factor()**

Add to `tests/test_scales.py`:

```python
from main import detect_scale_factor


def test_detect_scale_factor_reference():
    """1080p screen returns factor 1.0."""
    assert detect_scale_factor(1080) == 1.0


def test_detect_scale_factor_qhd():
    """1440p screen returns factor ~1.33."""
    assert detect_scale_factor(1440) == round(1440 / 1080, 2)


def test_detect_scale_factor_4k():
    """2160p screen returns factor 2.0."""
    assert detect_scale_factor(2160) == 2.0


def test_detect_scale_factor_clamp_low():
    """Small screens clamp to 1.0."""
    assert detect_scale_factor(768) == 1.0


def test_detect_scale_factor_clamp_high():
    """Very large screens clamp to 2.0."""
    assert detect_scale_factor(4320) == 2.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_scales.py::test_detect_scale_factor_reference -v`
Expected: FAIL — `detect_scale_factor` not importable

- [ ] **Step 3: Add detect_scale_factor() to main.py and update startup**

In `main.py`, add the function before `if __name__`:

```python
REFERENCE_HEIGHT = 1080
MAX_SCALE = 2.0


def detect_scale_factor(screen_height):
    """Compute UI scale factor from screen logical height."""
    return min(max(1.0, round(screen_height / REFERENCE_HEIGHT, 2)), MAX_SCALE)
```

Update the `if __name__` block:

```python
if __name__ == "__main__":
    log.info("App started")
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Detect scale factor from primary screen
    screen = app.primaryScreen()
    if screen:
        height = screen.availableSize().height()
        factor = detect_scale_factor(height)
        log.info("Screen height: %d, scale factor: %.2f", height, factor)
    else:
        factor = 1.0
        log.warning("No screen detected, using factor 1.0")
    init_scale(factor)

    load_fonts()
    app.setFont(QFont("Lexend"))
    window = SettingsWindow()
    window.show()
    sys.exit(app.exec())
```

Add import at top of `main.py`:

```python
from ui.scales import init_scale
```

- [ ] **Step 4: Run all tests**

Run: `python -m pytest tests/ -x -q`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add main.py tests/test_scales.py
git commit -m "feat: detect screen resolution and apply scale factor at startup"
```

---

### Task 4: Migrate viewer_window.py

**Files:**
- Modify: `ui/viewer_window.py`

- [ ] **Step 1: Replace top-level constants with S imports**

Remove the hardcoded constants at the top of the file:

```python
# DELETE these lines:
CORNER_GRIP = 50
MIN_WIDTH = 200
MIN_HEIGHT = 150
NAV_ZONE = 40
```

Add import:

```python
from ui.scales import S, sc
```

Replace all references throughout the file:
- `CORNER_GRIP` → `S.VIEWER_CORNER_GRIP`
- `MIN_WIDTH` → `S.VIEWER_MIN_W`
- `MIN_HEIGHT` → `S.VIEWER_MIN_H`
- `NAV_ZONE` → `S.VIEWER_NAV_ZONE`

- [ ] **Step 2: Replace hardcoded widget sizes**

Find and replace each hardcoded size:

- `setFixedHeight(3)` (progress bar) → `setFixedHeight(S.VIEWER_PROGRESS_H)`
- `setFixedSize(60, 60)` (center button) → `setFixedSize(S.VIEWER_CENTER_BTN, S.VIEWER_CENTER_BTN)`
- `setFixedSize(20, 20)` (alarm/coffee/icon labels) → `setFixedSize(S.VIEWER_ICON_LABEL, S.VIEWER_ICON_LABEL)`

- [ ] **Step 3: Replace hardcoded stylesheet font sizes**

- `font-size: 20px` → `f"font-size: {S.FONT_TIMER}px"`
- `font-size: 13px` → `f"font-size: {S.FONT_COUNTER}px"`
- `font-size: 14px` → `f"font-size: {S.FONT_HELP}px"`

- [ ] **Step 4: Replace hardcoded layout values in resizeEvent and _layout_bottom**

In `resizeEvent`:
- `btn_sz = 26` → `btn_sz = S.VIEWER_ICON_BTN`
- `margin = 8` → `margin = S.VIEWER_ICON_MARGIN`
- `gap = 4` → `gap = S.VIEWER_ICON_GAP`
- Left nav geometry: use `S.VIEWER_LEFT_NAV_X`, `S.VIEWER_LEFT_NAV_W`, `S.VIEWER_LEFT_NAV_H`

In `_layout_bottom`:
- `lbl_h = 24` → `lbl_h = S.VIEWER_BOTTOM_LABEL_H`
- `bottom_y = h - lbl_h - 8` → `bottom_y = h - lbl_h - S.VIEWER_BOTTOM_OFFSET`
- `x = 10` → `x = S.VIEWER_BOTTOM_LABEL_X`
- `x += 26` → `x += S.VIEWER_BOTTOM_ICON_SPACING`
- `bottom_y + 2` → `bottom_y + S.VIEWER_BOTTOM_ICON_Y_OFFSET`

In help overlay:
- `setContentsMargins(20, 20, 20, 20)` → use `S.VIEWER_HELP_MARGIN` for all four

- [ ] **Step 5: Run all tests**

Run: `python -m pytest tests/ -x -q`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add ui/viewer_window.py
git commit -m "refactor: migrate viewer_window.py to centralized scales"
```

---

### Task 5: Migrate editor_panel.py

**Files:**
- Modify: `ui/editor_panel.py`

- [ ] **Step 1: Replace top-level constants**

Remove:
```python
GRID_MIN = 48
GRID_MAX = 256
GRID_DEFAULT = 80
ZOOM_STEP = 16
```

Add `from ui.scales import S, sc` if not present. Replace all references:
- `GRID_MIN` → `S.GRID_MIN`
- `GRID_MAX` → `S.GRID_MAX`
- `GRID_DEFAULT` → `S.GRID_DEFAULT`
- `ZOOM_STEP` → `S.GRID_ZOOM_STEP`

- [ ] **Step 2: Replace hardcoded widget sizes and spacing**

- `setFixedHeight(1)` (color line) → `setFixedHeight(S.COLOR_LINE_H)`
- `setFixedWidth(90)` (zoom slider) → `setFixedWidth(S.ZOOM_SLIDER_W)`
- `len(items) * 30 + 4` → `len(items) * S.LIST_ITEM_H + S.LIST_PADDING`
- `setSpacing(4)` (list/grid) → `setSpacing(S.LIST_SPACING)` / `setSpacing(S.GRID_SPACING)`

- [ ] **Step 3: Replace hardcoded stylesheet values**

Scrollbar styles:
- `width: 4px` → `f"width: {S.SCROLLBAR_W}px"`
- `min-height: 20px` → `f"min-height: {S.SCROLLBAR_HANDLE_MIN_H}px"`
- `border-radius: 2px` → `f"border-radius: {S.SCROLLBAR_RADIUS}px"`

Slider styles:
- `height: 4px` → `f"height: {S.SLIDER_GROOVE_H}px"`
- `width: 12px` → `f"width: {S.SLIDER_HANDLE_W}px"`
- `margin: -4px 0` → `f"margin: -{S.SLIDER_HANDLE_MARGIN}px 0"`

Item/header padding:
- `padding: 2px` → `f"padding: {S.LIST_ITEM_PADDING}px"`
- `padding: 3px 2px 1px` → `f"padding: {S.HEADER_PADDING_TOP}px {S.HEADER_PADDING_H}px {S.HEADER_PADDING_BOTTOM}px"`
- `font-size: 12px` → `f"font-size: {S.FONT_MSG_BOX}px"`

Border widths:
- `border: 2px solid` → `f"border: {S.EDITOR_BORDER_SELECTED}px solid"`
- `border: 1px dashed` → `f"border: {S.EDITOR_BORDER_DASHED}px dashed"`

- [ ] **Step 4: Replace pin overlay positioning**

- `pin_sz + 2` → `pin_sz + S.PIN_OVERLAY_PADDING`
- `lbl.width() - psz - 4, 2` → `lbl.width() - psz - S.PIN_POS_X_OFFSET, S.PIN_POS_Y_OFFSET`

- [ ] **Step 5: Replace addRoundedRect radius**

- `addRoundedRect(..., 3, 3)` → `addRoundedRect(..., S.GRID_TILE_RADIUS, S.GRID_TILE_RADIUS)`

- [ ] **Step 6: Run all tests**

Run: `python -m pytest tests/ -x -q`
Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
git add ui/editor_panel.py
git commit -m "refactor: migrate editor_panel.py to centralized scales"
```

---

### Task 6: Migrate accent_picker.py

**Files:**
- Modify: `ui/accent_picker.py`

- [ ] **Step 1: Replace all hardcoded values**

Remove top-level constants `SQ = 120` and `BAR_W = 12`. Add `from ui.scales import S, sc`.

Replace:
- `SQ` → `S.ACCENT_SQ`
- `BAR_W` → `S.ACCENT_BAR_W`
- `setContentsMargins(10, 10, 10, 10)` → use `S.ACCENT_MARGIN`
- `setSpacing(8)` → `S.ACCENT_SPACING`
- `setSpacing(6)` → `S.ACCENT_ROW_SPACING`
- `setFixedHeight(20)` → `S.ACCENT_HEX_H`
- `border-radius: 2px` → `f"border-radius: {S.ACCENT_HEX_RADIUS}px"`
- `font-size: 10px` → `f"font-size: {S.ACCENT_HEX_FONT}px"`
- `pos.y() + 4` → `pos.y() + S.ACCENT_OFFSET_Y`

- [ ] **Step 2: Run all tests**

Run: `python -m pytest tests/ -x -q`
Expected: ALL PASS

- [ ] **Step 3: Commit**

```bash
git add ui/accent_picker.py
git commit -m "refactor: migrate accent_picker.py to centralized scales"
```

---

### Task 7: Migrate timer_panel.py

**Files:**
- Modify: `ui/timer_panel.py`

- [ ] **Step 1: Replace hardcoded values**

Add `from ui.scales import S, sc` if not present.

- `setFixedHeight(28)` (both mode buttons) → `setFixedHeight(S.TIMER_MODE_BTN_H)`
- `padding: 4px 8px` → `f"padding: {S.MODE_BTN_PADDING_V}px {S.MODE_BTN_PADDING_H}px"`

- [ ] **Step 2: Run all tests**

Run: `python -m pytest tests/ -x -q`
Expected: ALL PASS

- [ ] **Step 3: Commit**

```bash
git add ui/timer_panel.py
git commit -m "refactor: migrate timer_panel.py to centralized scales"
```

---

### Task 8: Migrate image_editor_window.py and snap.py

**Files:**
- Modify: `ui/image_editor_window.py`
- Modify: `ui/snap.py`

- [ ] **Step 1: Migrate image_editor_window.py**

Remove `EDGE = 6`. Add `from ui.scales import S, sc` if not present.

- `EDGE` → `S.RESIZE_GRIP_W`
- `setMinimumSize(200, 200)` → `setMinimumSize(S.EDITOR_MIN_W, S.EDITOR_MIN_H)`
- `setSpacing(4)` (title bar) → `setSpacing(S.EDITOR_TITLE_SPACING)`
- `addSpacing(6)` → `addSpacing(S.EDITOR_TITLE_BOTTOM_SPACE)`
- `snap = 12` → `snap = S.EDGE_SNAP_THRESHOLD`

- [ ] **Step 2: Migrate snap.py**

Remove `SNAP_DISTANCE = 15` and `DETACH_DISTANCE = 40`. Add `from ui.scales import S`.

- `SNAP_DISTANCE` → `S.SNAP_DISTANCE`
- `DETACH_DISTANCE` → `S.DETACH_DISTANCE`

- [ ] **Step 3: Run all tests**

Run: `python -m pytest tests/ -x -q`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add ui/image_editor_window.py ui/snap.py
git commit -m "refactor: migrate image_editor_window.py and snap.py to centralized scales"
```

---

### Task 9: Migrate bottom_bar.py

**Files:**
- Modify: `ui/bottom_bar.py`

- [ ] **Step 1: Replace hardcoded values**

Add `from ui.scales import S, sc` if not present.

- `setSpacing(4)` (summary time) → `setSpacing(S.SUMMARY_TIME_SPACING)`
- `addSpacing(8)` (before start button) → `addSpacing(S.START_BTN_SPACING)`
- `font-size: 9px` (limit button) → `f"font-size: {S.FONT_LIMIT_BTN}px"`
- `font-size: 10px` (limit separator) → `f"font-size: {S.FONT_LIMIT_SEP}px"`

- [ ] **Step 2: Run all tests**

Run: `python -m pytest tests/ -x -q`
Expected: ALL PASS

- [ ] **Step 3: Commit**

```bash
git add ui/bottom_bar.py
git commit -m "refactor: migrate bottom_bar.py to centralized scales"
```

---

### Task 10: Migrate url_dialog.py

**Files:**
- Modify: `ui/url_dialog.py`

- [ ] **Step 1: Replace all hardcoded values**

Add `from ui.scales import S, sc`.

Layout:
- `setMinimumWidth(400)` → `setMinimumWidth(S.URL_DLG_MIN_W)`
- `setContentsMargins(16, 12, 16, 12)` → use `S.URL_DLG_MARGIN_H`, `S.URL_DLG_MARGIN_V`
- `setSpacing(8)` → `S.URL_DLG_SPACING`
- `setSpacing(6)` → `S.URL_ROW_SPACING`
- `setMinimumHeight(200)` → `S.URL_FILE_LIST_MIN_H`
- `setIconSize(QSize(48, 48))` → `QSize(S.URL_PREVIEW_SIZE, S.URL_PREVIEW_SIZE)`

Stylesheets:
- `font-size: 11px` → `f"font-size: {S.URL_INPUT_FONT}px"`
- `font-size: 10px` → `f"font-size: {S.URL_BTN_FONT}px"`
- `padding: 6px` → `f"padding: {S.URL_INPUT_PADDING}px"`
- `padding: 3px 6px` → `f"padding: {S.URL_BTN_PADDING_V}px {S.URL_BTN_PADDING_H}px"`
- `padding: 3px` → `f"padding: {S.URL_LIST_ITEM_PADDING}px"`
- `height: 8px` → `f"height: {S.URL_PROGRESS_H}px"`

- [ ] **Step 2: Run all tests**

Run: `python -m pytest tests/ -x -q`
Expected: ALL PASS

- [ ] **Step 3: Commit**

```bash
git add ui/url_dialog.py
git commit -m "refactor: migrate url_dialog.py to centralized scales"
```

---

### Task 11: Migrate widgets.py and rounded_window.py

**Files:**
- Modify: `ui/widgets.py`
- Modify: `ui/rounded_window.py`

- [ ] **Step 1: Migrate widgets.py**

In TitleLabel.paintEvent, the emboss offsets:
- `adjusted(0, -1, 0, -1)` → `adjusted(0, -S.TEXT_SHADOW_OFFSET, 0, -S.TEXT_SHADOW_OFFSET)`
- `adjusted(0, 1, 0, 1)` → `adjusted(0, S.TEXT_SHADOW_OFFSET, 0, S.TEXT_SHADOW_OFFSET)`

In `make_centered_header`:
- `setSpacing(6)` → `setSpacing(S.SPACING_HEADER)`

- [ ] **Step 2: Migrate rounded_window.py**

- `QPen(border, 1)` → `QPen(border, S.BORDER_WIDTH)`

- [ ] **Step 3: Run all tests**

Run: `python -m pytest tests/ -x -q`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add ui/widgets.py ui/rounded_window.py
git commit -m "refactor: migrate widgets.py and rounded_window.py to centralized scales"
```

---

### Task 12: Integration test — verify scaling with manual factor

**Files:**
- Modify: `tests/test_scales.py`

- [ ] **Step 1: Add integration test**

```python
def test_all_base_values_recorded():
    """Every int attribute in S should be in _BASE."""
    from ui.scales import _BASE
    for attr in dir(S):
        if attr.startswith('_'):
            continue
        val = getattr(S, attr)
        if isinstance(val, int):
            assert attr in _BASE, f"S.{attr} not in _BASE dict"


def test_ratios_not_scaled():
    """Float ratios must not change after init_scale."""
    init_scale(2.0)
    assert S.START_ICON_RATIO == 0.75
    assert S.START_RADIUS_RATIO == 0.19
    init_scale(1.0)


def test_round_trip_all_constants():
    """init_scale(2.0) then init_scale(1.0) restores every constant."""
    from ui.scales import _BASE
    init_scale(2.0)
    init_scale(1.0)
    for attr, base_val in _BASE.items():
        actual = getattr(S, attr)
        assert actual == base_val, f"S.{attr}: expected {base_val}, got {actual}"
```

- [ ] **Step 2: Run full test suite**

Run: `python -m pytest tests/ -x -q`
Expected: ALL PASS

- [ ] **Step 3: Manual smoke test**

Temporarily modify `main.py` to force `factor = 1.5` (skip detection). Run the app and verify:
- Window is larger (375x375)
- All elements scale proportionally
- No clipping or overflow
- Fonts are readable

Revert the temporary change after testing.

- [ ] **Step 4: Commit**

```bash
git add tests/test_scales.py
git commit -m "test: add integration tests for DPI scaling"
```

---

### Task 13: Clean up unused imports and verify

**Files:**
- All modified files

- [ ] **Step 1: Verify no unused imports remain**

Check each migrated file for:
- Removed constants that are no longer defined locally
- `sc` import only where actually used (stylesheet strings)
- No leftover references to old constant names

- [ ] **Step 2: Run full test suite one final time**

Run: `python -m pytest tests/ -x -v`
Expected: ALL PASS, no warnings

- [ ] **Step 3: Commit any cleanup**

```bash
git add -A
git commit -m "chore: clean up imports after DPI scaling migration"
```
