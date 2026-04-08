# Settings Redesign Part 1: Theme & Scales Foundation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace hardcoded pixel values with centralized scales system, update theme palettes to A+C design, add start button icon and toggle icon definitions.

**Architecture:** New `ui/scales.py` defines all sizes as named constants. `ui/theme.py` updated with A+C palettes, accent-derived colors, and `start_text` property. `ui/icons.py` centralizes icon name/size definitions. All UI files import from these instead of hardcoding.

**Tech Stack:** Python, PyQt6, qtawesome

**Spec:** `docs/superpowers/specs/2026-04-08-settings-redesign.md`

---

### Task 1: Create scales.py

**Files:**
- Create: `ui/scales.py`
- Test: `tests/test_scales.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_scales.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ui.scales import S


def test_margins_defined():
    assert S.MARGIN == 14
    assert S.MARGIN_BOTTOM == 18


def test_icon_sizes():
    assert S.ICON_HEADER == 13
    assert S.ICON_DICE == 34
    assert S.ICON_START == 42


def test_start_button():
    assert S.START_ICON_RATIO == 0.75
    assert S.START_RADIUS_RATIO == 0.12


def test_font_sizes():
    assert S.FONT_TITLE == 11
    assert S.FONT_BUTTON == 10
    assert S.FONT_LABEL == 9
    assert S.FONT_DURATION == 18


def test_window_sizes():
    assert S.MAIN_W == 250
    assert S.MAIN_H == 270
    assert S.EDITOR_W == 250
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_scales.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ui.scales'`

- [ ] **Step 3: Write scales.py**

```python
# ui/scales.py
"""Centralized size definitions — single source of truth for all UI dimensions."""


class S:
    # Window
    MAIN_W = 250
    MAIN_H = 270
    EDITOR_W = 250

    # Margins
    MARGIN = 14
    MARGIN_BOTTOM = 18

    # Icons — header row
    ICON_HEADER = 13
    ACCENT_DOT = 11

    # Icons — bottom bar
    ICON_DICE = 34
    ICON_START = 42

    # Start button
    START_ICON_RATIO = 0.75
    START_RADIUS_RATIO = 0.12

    # Fonts (px)
    FONT_TITLE = 11
    FONT_BUTTON = 10
    FONT_LABEL = 9
    FONT_HINT = 8
    FONT_DURATION = 18
    FONT_TOTAL = 10

    # Spacing
    SPACING_HEADER = 6
    SPACING_MODE = 10
    SPACING_DURATION = 12
    SPACING_TIERS = 3
    SPACING_SUMMARY = 6

    # Duration picker
    DURATION_ARROW = 14
    DURATION_ARROW_BTN = 22

    # Timer buttons
    TIMER_BTN_PADDING_V = 4
    TIMER_BTN_PADDING_H = 7

    # Editor toolbar buttons
    EDITOR_BTN = 20
    EDITOR_BTN_ICON = 11
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_scales.py -v`
Expected: PASS (all 6 tests)

- [ ] **Step 5: Commit**

```bash
git add ui/scales.py tests/test_scales.py
git commit -m "feat: add centralized scales system (ui/scales.py)"
```

---

### Task 2: Update theme.py with A+C palettes

**Files:**
- Modify: `ui/theme.py`
- Modify: `tests/test_theme.py`

- [ ] **Step 1: Write failing tests for new properties**

Add to `tests/test_theme.py`:

```python
def test_start_text_dark():
    t = Theme("dark")
    assert t.start_text == "#252525"


def test_start_text_light():
    t = Theme("light")
    assert t.start_text == "#c4c4c4"


def test_warning_color():
    t = Theme("dark")
    assert t.warning == "#cc5555"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_theme.py::test_start_text_dark -v`
Expected: FAIL — `start_text` not in base palette

- [ ] **Step 3: Update theme.py**

Update `_DARK_BASE` and `_LIGHT_BASE` in `ui/theme.py`:

```python
_DARK_BASE = {
    "bg": "#191919",
    "bg_secondary": "#171717",
    "bg_row_even": "#1f1f1f",
    "bg_row_odd": "#252525",
    "bg_button": "#222222",
    "border": "#303030",
    "text_primary": "#ddd",
    "text_secondary": "#606060",
    "text_hint": "#454545",
    "start_text": "#252525",
    "warning": "#cc5555",
}

_LIGHT_BASE = {
    "bg": "#d4d4d4",
    "bg_secondary": "#dddddd",
    "bg_row_even": "#d8d8d8",
    "bg_row_odd": "#d2d2d2",
    "bg_button": "#c6c6c6",
    "border": "#a5a5a5",
    "text_primary": "#222",
    "text_secondary": "#5a5a5a",
    "text_hint": "#858585",
    "start_text": "#c4c4c4",
    "warning": "#cc4444",
}
```

- [ ] **Step 4: Update existing tests for new palette values**

Update `test_dark_theme_has_required_keys` and `test_light_theme_has_required_keys` to match new hex values. Update `test_toggle` similarly.

- [ ] **Step 5: Run all theme tests**

Run: `python -m pytest tests/test_theme.py -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add ui/theme.py tests/test_theme.py
git commit -m "feat: update theme to A+C palette with start_text and warning colors"
```

---

### Task 3: Create icons.py

**Files:**
- Create: `ui/icons.py`
- Test: `tests/test_icons.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_icons.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ui.icons import Icons


def test_start_icon():
    assert Icons.START == "fa6s.pencil"


def test_random_toggle():
    assert Icons.RANDOM_ON == "ph.dice-five-fill"
    assert Icons.RANDOM_OFF == "ph.dice-three-bold"


def test_topmost_toggle():
    assert Icons.TOPMOST_ON == "ph.push-pin-fill"
    assert Icons.TOPMOST_OFF == "ph.push-pin-bold"


def test_theme_toggle():
    assert Icons.THEME_DARK == "ph.moon-bold"
    assert Icons.THEME_LIGHT == "ph.sun-bold"


def test_editor_icons():
    assert Icons.ADD_FILE == "ph.file-plus-bold"
    assert Icons.ADD_FOLDER == "ph.folder-plus-bold"
    assert Icons.ADD_URL == "ph.link-bold"
    assert Icons.ERASER == "ph.eraser-bold"
    assert Icons.CLOSE == "ph.x-bold"
    assert Icons.DETACH == "ph.arrow-square-out-bold"
    assert Icons.DOCK == "ph.arrows-in-bold"
    assert Icons.INFO == "ph.info-bold"
    assert Icons.PLUS == "ph.plus-bold"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_icons.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write icons.py**

```python
# ui/icons.py
"""Centralized icon name definitions."""


class Icons:
    # Start button
    START = "fa6s.pencil"

    # Toggle: random order
    RANDOM_ON = "ph.dice-five-fill"
    RANDOM_OFF = "ph.dice-three-bold"

    # Toggle: always on top
    TOPMOST_ON = "ph.push-pin-fill"
    TOPMOST_OFF = "ph.push-pin-bold"

    # Theme toggle
    THEME_DARK = "ph.moon-bold"
    THEME_LIGHT = "ph.sun-bold"

    # Navigation
    CARET_LEFT = "ph.caret-left-bold"
    CARET_RIGHT = "ph.caret-right-bold"
    INFO = "ph.info-bold"
    PLUS = "ph.plus-bold"

    # Editor toolbar
    ADD_FILE = "ph.file-plus-bold"
    ADD_FOLDER = "ph.folder-plus-bold"
    ADD_URL = "ph.link-bold"
    ERASER = "ph.eraser-bold"
    CLOSE = "ph.x-bold"
    DETACH = "ph.arrow-square-out-bold"
    DOCK = "ph.arrows-in-bold"
    TRASH = "ph.trash-bold"

    # View modes
    LIST = "ph.list-bullets-bold"
    GRID = "ph.squares-four-bold"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_icons.py -v`
Expected: PASS (all 5 tests)

- [ ] **Step 5: Commit**

```bash
git add ui/icons.py tests/test_icons.py
git commit -m "feat: add centralized icon definitions (ui/icons.py)"
```

---

### Task 4: Run full test suite

- [ ] **Step 1: Run all tests**

Run: `python -m pytest tests/ -v`
Expected: ALL PASS (existing 103 + new ~17 = ~120 tests)

- [ ] **Step 2: Verify app still launches**

Run: `python -c "from ui.settings_window import SettingsWindow; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit if any fixes needed**

```bash
git add -A
git commit -m "fix: ensure all tests pass after theme/scales/icons foundation"
```

---

## Plan Self-Review

- [x] Spec coverage: scales, theme update, icons — all foundation elements covered
- [x] No placeholders — all code blocks complete
- [x] Type consistency — `S.`, `Icons.`, `Theme()` used consistently
- [x] Existing code not broken — theme.py extends, doesn't replace
- [x] Tests first in every task

## Next Plans
- **Part 2:** Main window redesign (settings_window.py rewrite using scales/icons/theme)
- **Part 3:** Editor panel redesign (image_editor_window.py rewrite + dock system)
