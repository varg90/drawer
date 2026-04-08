# Settings Redesign Part 2: Main Window Rewrite

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite settings_window.py to match the new 250x270 compact design with centered REFBOT, unified timer layout, icon toggles, and fa6s.pencil start button.

**Architecture:** New `ui/widgets.py` with reusable widget factories. `settings_window.py` rewritten with new `_build_ui` using scales/icons/theme. Logic methods (timer, session, images, slideshow) preserved. Old widget classes removed.

**Tech Stack:** Python, PyQt6, qtawesome, ui/scales.py, ui/icons.py, ui/theme.py

**Spec:** `docs/superpowers/specs/2026-04-08-settings-redesign.md`

**Depends on:** Plan 1 (scales, theme, icons) — completed.

---

### Task 1: Update constants — add 2m preset

**Files:**
- Modify: `core/constants.py`
- Modify: `tests/test_constants.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_constants.py`:

```python
def test_timer_presets_has_2min():
    from core.constants import TIMER_PRESETS
    secs = [s for s, _ in TIMER_PRESETS]
    assert 120 in secs
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_constants.py::test_timer_presets_has_2min -v`
Expected: FAIL

- [ ] **Step 3: Add 2m to TIMER_PRESETS in constants.py**

In `core/constants.py`, insert `(120, "2м")` after `(60, "1м")`:

```python
TIMER_PRESETS = [
    (30, "30с"),
    (60, "1м"),
    (120, "2м"),
    (300, "5м"),
    (600, "10м"),
    (900, "15м"),
    (1800, "30м"),
    (3600, "1ч"),
]
```

- [ ] **Step 4: Run test to verify passes**

Run: `python -m pytest tests/test_constants.py -v`
Expected: ALL PASS

- [ ] **Step 5: Update settings_window.py default _preset_index**

The default was `self._preset_index = 2` (5min). With the new 2м entry, 5min is now index 3. Update:

```python
self._preset_index = 3  # default 5min
```

- [ ] **Step 6: Run full tests + commit**

Run: `python -m pytest tests/ -q`
Expected: ALL PASS

```bash
git add core/constants.py tests/test_constants.py ui/settings_window.py
git commit -m "feat: add 2m timer preset"
```

---

### Task 2: Create ui/widgets.py — reusable widget factories

**Files:**
- Create: `ui/widgets.py`
- Test: `tests/test_widgets.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_widgets.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ui.widgets import make_icon_btn, make_start_btn, make_icon_toggle
from ui.scales import S
from ui.icons import Icons


def test_make_icon_btn_returns_callable():
    assert callable(make_icon_btn)


def test_make_start_btn_returns_callable():
    assert callable(make_start_btn)


def test_make_icon_toggle_returns_callable():
    assert callable(make_icon_toggle)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_widgets.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write ui/widgets.py**

```python
# ui/widgets.py
"""Reusable widget factories for RefBot UI."""
import qtawesome as qta
from PyQt6.QtWidgets import QPushButton, QLabel, QHBoxLayout, QWidget
from PyQt6.QtCore import Qt, QSize
from ui.scales import S
from ui.icons import Icons


def make_icon_btn(icon_name, color, size=S.ICON_HEADER, tooltip=""):
    """Small icon button with no background/border."""
    btn = QPushButton()
    btn.setIcon(qta.icon(icon_name, color=color))
    btn.setIconSize(QSize(size, size))
    btn.setFixedSize(size, size)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet("background: transparent; border: none; padding: 0px;")
    if tooltip:
        btn.setToolTip(tooltip)
    return btn


def make_start_btn(theme):
    """Square start button with fa6s.pencil icon."""
    size = S.ICON_START
    icon_sz = int(size * S.START_ICON_RATIO)
    radius = int(size * S.START_RADIUS_RATIO)
    btn = QPushButton()
    btn.setIcon(qta.icon(Icons.START, color=theme.start_text))
    btn.setIconSize(QSize(icon_sz, icon_sz))
    btn.setFixedSize(size, size)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet(
        f"background-color: {theme.start_bg}; border: none; "
        f"border-radius: {radius}px;")
    return btn


def make_icon_toggle(icon_on, icon_off, is_on, theme, size=S.ICON_HEADER):
    """Toggle button that switches between two icons."""
    btn = QPushButton()
    icon_name = icon_on if is_on else icon_off
    color = theme.accent if is_on else theme.text_hint
    btn.setIcon(qta.icon(icon_name, color=color))
    btn.setIconSize(QSize(size, size))
    btn.setFixedSize(size, size)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet("background: transparent; border: none; padding: 0px;")
    return btn


def make_centered_header(title_text, left_widgets, right_widgets, theme):
    """Header row with title centered via equal stretch containers."""
    header = QHBoxLayout()
    header.setContentsMargins(0, 0, 0, 0)
    header.setSpacing(0)

    left_box = QHBoxLayout()
    left_box.setSpacing(2)
    left_box.setContentsMargins(0, 0, 0, 0)
    for w in left_widgets:
        left_box.addWidget(w)
    left_box.addStretch()
    lw = QWidget()
    lw.setLayout(left_box)
    lw.setStyleSheet("background: transparent;")

    right_box = QHBoxLayout()
    right_box.setSpacing(2)
    right_box.setContentsMargins(0, 0, 0, 0)
    right_box.addStretch()
    for w in right_widgets:
        right_box.addWidget(w)
    rw = QWidget()
    rw.setLayout(right_box)
    rw.setStyleSheet("background: transparent;")

    title = QLabel(title_text)
    title.setAlignment(Qt.AlignmentFlag.AlignCenter)
    title.setStyleSheet(
        f"color: {theme.text_header}; font-size: {S.FONT_TITLE}px; "
        f"font-weight: 500; letter-spacing: 3px;")

    header.addWidget(lw, 1)
    header.addWidget(title)
    header.addWidget(rw, 1)
    return header, title


def make_timer_btn(label, is_active, theme):
    """Timer preset or tier button."""
    btn = QPushButton(label)
    if is_active:
        btn.setStyleSheet(
            f"background-color: {theme.bg_active}; color: {theme.text_primary}; "
            f"border: 1px solid {theme.border_active}; "
            f"font-size: {S.FONT_BUTTON}px; "
            f"padding: {S.TIMER_BTN_PADDING_V}px {S.TIMER_BTN_PADDING_H}px;")
    else:
        btn.setStyleSheet(
            f"background-color: {theme.bg_button}; color: {theme.text_secondary}; "
            f"border: 1px solid {theme.border}; "
            f"font-size: {S.FONT_BUTTON}px; "
            f"padding: {S.TIMER_BTN_PADDING_V}px {S.TIMER_BTN_PADDING_H}px;")
    return btn
```

- [ ] **Step 4: Run test to verify passes**

Run: `python -m pytest tests/test_widgets.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add ui/widgets.py tests/test_widgets.py
git commit -m "feat: add reusable widget factories (ui/widgets.py)"
```

---

### Task 3: Rewrite settings_window.py — _build_ui

This is the core task. Rewrite the entire `_build_ui` method to use the new layout. Keep all logic methods unchanged.

**Files:**
- Modify: `ui/settings_window.py`

- [ ] **Step 1: Update imports**

Replace imports at top of `settings_window.py`:

```python
import os
import qtawesome as qta
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                              QPushButton, QLabel, QFileDialog, QApplication)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QColor
from core.constants import SUPPORTED_FORMATS, TIMER_PRESETS, SESSION_PRESETS
from core.timer_logic import format_time
from core.class_mode import auto_distribute, groups_to_timers, total_duration
from core.file_utils import filter_image_files, scan_folder
from core.session import save_session, load_session
from core.models import ImageItem
from ui.theme import Theme
from ui.scales import S
from ui.icons import Icons
from ui.widgets import (make_icon_btn, make_start_btn, make_icon_toggle,
                         make_centered_header, make_timer_btn)
```

- [ ] **Step 2: Remove old widget classes**

Delete `ThemeToggleButton`, `SegmentButton`, `PresetButton` classes. Keep `TierToggle` temporarily (will be replaced by make_timer_btn).

- [ ] **Step 3: Update ALL_TIERS to match new presets**

```python
ALL_TIERS = [(30, "30с"), (60, "1м"), (180, "3м"),
             (300, "5м"), (600, "10м"), (900, "15м"),
             (1800, "30м"), (3600, "1ч")]
```

(No change needed — already matches.)

- [ ] **Step 4: Rewrite __init__**

```python
class SettingsWindow(QMainWindow):
    images_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("RefBot")
        self.images = []
        self.viewer = None
        self.editor = None
        self.theme = Theme("dark")

        self._timer_mode = "class"  # default to class (was "standard")
        self._preset_index = 3  # default 5min (index 3 after adding 2m)
        self._session_index = 5  # default 1h
        self._manual_groups = []
        self._class_groups = []

        self._build_ui()
        self._apply_theme()
        self._restore_session()
        self.setAcceptDrops(True)
        self.setFixedSize(S.MAIN_W, S.MAIN_H)
```

- [ ] **Step 5: Rewrite _build_ui**

```python
def _build_ui(self):
    central = QWidget()
    self.setCentralWidget(central)
    root = QVBoxLayout(central)
    root.setContentsMargins(S.MARGIN, S.MARGIN, S.MARGIN, S.MARGIN_BOTTOM)
    root.setSpacing(0)

    # Header: info + pin left | REFBOT | accent + moon right
    self._info_btn = make_icon_btn(Icons.INFO, self.theme.text_hint)
    self._info_btn.clicked.connect(self._show_help)
    self._pin_btn = make_icon_toggle(
        Icons.TOPMOST_ON, Icons.TOPMOST_OFF, False, self.theme)
    self._pin_btn.clicked.connect(self._toggle_topmost)

    self._accent_btn = QPushButton()
    self._accent_btn.setFixedSize(S.ACCENT_DOT, S.ACCENT_DOT)
    self._accent_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    self._accent_btn.clicked.connect(self._pick_accent)

    self._theme_btn = make_icon_btn(
        Icons.THEME_DARK, self.theme.text_hint)
    self._theme_btn.clicked.connect(self._toggle_theme)

    self._header, self._title = make_centered_header(
        "REFBOT",
        [self._info_btn, self._pin_btn],
        [self._accent_btn, self._theme_btn],
        self.theme)
    root.addLayout(self._header)
    root.addSpacing(S.SPACING_HEADER)

    # Mode toggle + count + add
    mode_row = QHBoxLayout()
    mode_row.setContentsMargins(0, 0, 0, 0)
    mode_row.setSpacing(0)
    self._class_btn = QPushButton("Class")
    self._quick_btn = QPushButton("Quick")
    self._class_btn.clicked.connect(lambda: self._set_timer_mode("class"))
    self._quick_btn.clicked.connect(lambda: self._set_timer_mode("quick"))
    mode_row.addWidget(self._class_btn)
    mode_row.addWidget(self._quick_btn)
    mode_row.addStretch()
    self._count_label = QLabel("")
    mode_row.addWidget(self._count_label)
    mode_row.addSpacing(2)
    self._add_btn = make_icon_btn(Icons.PLUS, self.theme.text_button, size=20)
    self._add_btn.setStyleSheet(
        f"background-color: {self.theme.bg_button}; "
        f"border: 1px solid {self.theme.border};")
    self._add_btn.clicked.connect(self._open_editor)
    mode_row.addWidget(self._add_btn)
    root.addLayout(mode_row)
    root.addSpacing(S.SPACING_MODE)

    # Duration picker — always present
    dur_row = QHBoxLayout()
    dur_row.addStretch()
    self._dur_left = QPushButton()
    self._dur_left.setFixedSize(S.DURATION_ARROW_BTN, S.DURATION_ARROW_BTN)
    self._dur_left.setStyleSheet("background: transparent; border: none;")
    self._dur_left.clicked.connect(self._prev_session)
    dur_row.addWidget(self._dur_left)
    self._dur_display = QLabel("1:00:00")
    self._dur_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
    dur_row.addWidget(self._dur_display)
    self._dur_right = QPushButton()
    self._dur_right.setFixedSize(S.DURATION_ARROW_BTN, S.DURATION_ARROW_BTN)
    self._dur_right.setStyleSheet("background: transparent; border: none;")
    self._dur_right.clicked.connect(self._next_session)
    dur_row.addWidget(self._dur_right)
    dur_row.addStretch()
    root.addLayout(dur_row)
    root.addSpacing(S.SPACING_DURATION)

    # Timer buttons — both modes use same layout
    self._timer_buttons = []
    if self._timer_mode == "quick":
        preset_labels = [("30s", 30), ("1m", 60), ("2m", 120), ("5m", 300),
                         ("10m", 600), ("15m", 900), ("30m", 1800), ("1h", 3600)]
    else:
        preset_labels = [("30s", 30), ("1m", 60), ("3m", 180), ("5m", 300),
                         ("10m", 600), ("15m", 900), ("30m", 1800), ("1h", 3600)]
    for row_start in range(0, 8, 4):
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(S.SPACING_TIERS)
        for label, secs in preset_labels[row_start:row_start+4]:
            btn = make_timer_btn(label, False, self.theme)
            btn._secs = secs
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, s=secs: self._on_timer_btn(s))
            self._timer_buttons.append(btn)
            row.addWidget(btn)
        row.addStretch()
        root.addLayout(row)
        root.addSpacing(S.SPACING_TIERS)

    root.addSpacing(S.SPACING_SUMMARY)

    # Summary + total
    self._summary = QLabel("")
    self._summary.setStyleSheet(
        f"color: {self.theme.text_secondary}; font-size: {S.FONT_LABEL}px;")
    root.addWidget(self._summary)
    root.addSpacing(2)
    self._total = QLabel("")
    self._total.setStyleSheet(
        f"color: {self.theme.text_primary}; font-size: {S.FONT_TOTAL}px;")
    root.addWidget(self._total)

    root.addStretch()

    # Bottom bar: dice left, start right
    bot = QHBoxLayout()
    bot.setContentsMargins(0, 0, 0, 0)
    bot.setSpacing(6)
    self._dice_btn = make_icon_toggle(
        Icons.RANDOM_ON, Icons.RANDOM_OFF, False,
        self.theme, size=S.ICON_DICE)
    self._dice_btn.clicked.connect(self._toggle_random)
    bot.addWidget(self._dice_btn,
                  alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
    bot.addStretch()
    self._start_btn = make_start_btn(self.theme)
    self._start_btn.clicked.connect(self._start_slideshow)
    bot.addWidget(self._start_btn, alignment=Qt.AlignmentFlag.AlignBottom)
    root.addLayout(bot)
```

Note: This is the layout structure. The actual implementation will need adaptation for the existing logic methods (`_set_timer_mode`, `_select_preset_by_secs`, `_auto_distribute`, etc). The implementer should:
- Keep all existing logic methods from current settings_window.py
- Map "standard" mode to "quick" internally
- Map "session" mode to "class" internally
- Keep `_update_preset_styles`, `_update_tier_styles` but refactor to use `make_timer_btn`
- Keep `_show_help`, `_toggle_theme`, `_pick_accent`
- Add `_toggle_topmost` (reads/writes `self._topmost` bool, updates pin icon)
- Add `_toggle_random` (reads/writes `self._random` bool, updates dice icon)
- Keep all session save/restore, image management, drag/drop, slideshow methods

- [ ] **Step 6: Test build**

Run: `python -c "from ui.settings_window import SettingsWindow; print('OK')"`
Expected: `OK`

- [ ] **Step 7: Commit**

```bash
git add ui/settings_window.py
git commit -m "feat: rewrite settings window layout to new compact design"
```

---

### Task 4: Rewrite _apply_theme using scales

**Files:**
- Modify: `ui/settings_window.py`

- [ ] **Step 1: Rewrite _apply_theme**

All stylesheet values should use `S.*` constants and `self.theme.*` colors. No hardcoded pixel values.

Key patterns:
- `font-size: {S.FONT_BUTTON}px` instead of `font-size: 10px`
- `color: {t.text_secondary}` instead of `color: #606060`
- `padding: {S.TIMER_BTN_PADDING_V}px {S.TIMER_BTN_PADDING_H}px`

Must update: title, mode buttons, duration picker, timer buttons, summary, total, accent dot, all icons.

- [ ] **Step 2: Update duration picker state for Quick mode**

Duration picker dimmed in Quick mode:
```python
def _update_duration_picker(self):
    t = self.theme
    is_class = self._timer_mode == "class"
    arrow_color = t.text_secondary if is_class else t.text_hint
    time_color = t.text_primary if is_class else t.text_hint
    self._dur_left.setIcon(qta.icon(Icons.CARET_LEFT, color=arrow_color))
    self._dur_left.setIconSize(QSize(S.DURATION_ARROW, S.DURATION_ARROW))
    self._dur_left.setEnabled(is_class)
    self._dur_right.setIcon(qta.icon(Icons.CARET_RIGHT, color=arrow_color))
    self._dur_right.setIconSize(QSize(S.DURATION_ARROW, S.DURATION_ARROW))
    self._dur_right.setEnabled(is_class)
    self._dur_display.setStyleSheet(
        f"color: {time_color}; font-size: {S.FONT_DURATION}px; font-weight: 400;")
```

- [ ] **Step 3: Test launch + theme toggle**

Run: `python -c "from ui.settings_window import SettingsWindow; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add ui/settings_window.py
git commit -m "feat: rewrite _apply_theme with scales and theme system"
```

---

### Task 5: Update session persistence

**Files:**
- Modify: `ui/settings_window.py`

- [ ] **Step 1: Update _save_session**

Add `view_mode` to saved data. Map internal mode names:
- `"class"` saves as `"class"` (was `"class"` mapped from `"session"`)
- `"quick"` saves as `"quick"` (was `"standard"`)

```python
def _save_session(self):
    data = {
        "images": [img.to_dict() for img in self.images],
        "timer_seconds": self.get_timer_seconds(),
        "timer_mode": self._timer_mode,
        "session_seconds": self._get_session_seconds(),
        "random_order": self._random,
        "topmost": self._topmost,
        "theme": self.theme.name,
        "accent": self.theme.accent,
        "tiers": [btn._secs for btn in self._timer_buttons
                  if hasattr(btn, '_secs') and btn.isChecked()],
        "view_mode": getattr(self, "_view_mode", "compact"),
        "editor_view": (self.editor._view_mode
                        if self.editor and self.editor.isVisible()
                        else getattr(self, "_last_editor_view", "list")),
        "viewer_size": getattr(self, "_last_viewer_size", None),
    }
    save_session(data)
```

- [ ] **Step 2: Update _restore_session**

Handle both old and new format:

```python
timer_mode = data.get("timer_mode", "class")
if timer_mode == "standard":
    timer_mode = "quick"
elif timer_mode in ("session", "class"):
    timer_mode = "class"
self._timer_mode = timer_mode
```

- [ ] **Step 3: Run all tests**

Run: `python -m pytest tests/ -q`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add ui/settings_window.py
git commit -m "feat: update session persistence for new mode names and view_mode"
```

---

### Task 6: Full integration test

- [ ] **Step 1: Run full test suite**

Run: `python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 2: Verify app launches and displays**

Run: `python main.py` (manual visual check — verify window appears at 250x270 with new layout)

- [ ] **Step 3: Verify theme toggle works**

Click moon/sun icon — dark/light switch.

- [ ] **Step 4: Verify mode switch works**

Click Class/Quick — layout stays same size, content changes.

- [ ] **Step 5: Commit any fixes**

```bash
git add -A
git commit -m "fix: integration fixes for settings redesign"
```

---

## Plan Self-Review

- [x] Spec coverage: window size, header, modes, duration picker, timer buttons, bottom bar, persistence — all covered
- [x] No placeholders — all code blocks have real code
- [x] Type consistency — `S.*`, `Icons.*`, `Theme.*` used consistently across tasks
- [x] Backwards compatibility — old session format handled in restore
- [x] TDD in Task 1-2, verification in Task 3-6

## Notes for Implementer

- **settings_window.py is 831 lines.** Task 3 is the biggest — rewriting _build_ui. Keep all logic methods from current file. Only the UI construction and styling changes.
- **"standard" → "quick", "session" → "class"** throughout. Internal variable `_timer_mode` uses new names.
- **TierToggle class** can be removed — timer buttons now use `make_timer_btn` with `setCheckable(True)`.
- **ThemeToggleButton, SegmentButton, PresetButton** classes — all removed, replaced by widgets.py factories.
- **Checkboxes removed** — "Random order" and "Always on top" are now icon toggles (dice and pin), stored as `self._random` and `self._topmost` bools.

## Next Plan
- **Part 3:** Editor panel redesign (image_editor_window.py rewrite + dock system)
