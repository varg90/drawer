# UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign RefBot settings window with minimal grey theme (dark/light), sharp corners, compact card layout, and a separate image editor window.

**Architecture:** Extract theme colors into a theme module. Rewrite settings_window.py as a compact vertical card. Create image_editor_window.py as a separate popup. Core logic modules stay untouched.

**Tech Stack:** Python, PyQt6, existing core/ modules

**Spec:** `docs/superpowers/specs/2026-04-06-ui-redesign-design.md`

---

## File Structure

| Action | File | Responsibility |
|--------|------|---------------|
| Create | `ui/theme.py` | Dark/light color palettes, theme toggle logic, stylesheet generation |
| Create | `tests/test_theme.py` | Tests for theme module |
| Rewrite | `ui/settings_window.py` | Compact card layout: drop zone, thumbnails, timer modes, start |
| Create | `ui/image_editor_window.py` | Separate image list editor with toolbar, drag-and-drop, up/down |
| Create | `tests/test_image_editor.py` | Tests for image editor data logic |
| Modify | `ui/image_list_widget.py` | Adapt for use inside image editor window |
| Modify | `main.py` | Remove old palette setup (theme handles it now) |

---

### Task 1: Theme Module

**Files:**
- Create: `ui/theme.py`
- Create: `tests/test_theme.py`

- [ ] **Step 1: Write failing tests for theme**

Create `tests/test_theme.py`:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ui.theme import Theme


def test_dark_theme_has_required_keys():
    t = Theme("dark")
    assert t.bg == "#1c1c1c"
    assert t.text_primary == "#ccc"
    assert t.text_secondary == "#555"


def test_light_theme_has_required_keys():
    t = Theme("light")
    assert t.bg == "#f0f0f0"
    assert t.text_primary == "#222"
    assert t.text_secondary == "#888"


def test_default_is_dark():
    t = Theme()
    assert t.bg == "#1c1c1c"


def test_toggle():
    t = Theme("dark")
    t.toggle()
    assert t.bg == "#f0f0f0"
    t.toggle()
    assert t.bg == "#1c1c1c"


def test_name_property():
    t = Theme("dark")
    assert t.name == "dark"
    t.toggle()
    assert t.name == "light"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_theme.py -v`
Expected: FAIL — `ui.theme` does not exist yet.

- [ ] **Step 3: Implement theme module**

Create `ui/theme.py`:

```python
"""Theme colors for dark and light modes."""


_DARK = {
    "bg": "#1c1c1c",
    "bg_secondary": "#1a1a1a",
    "bg_row_even": "#222",
    "bg_row_odd": "#282828",
    "bg_button": "#252525",
    "bg_active": "#333",
    "border": "#333",
    "border_active": "#444",
    "text_primary": "#ccc",
    "text_secondary": "#555",
    "text_hint": "#444",
    "text_header": "#777",
    "text_button": "#777",
    "start_bg": "#555",
    "start_text": "#eee",
}

_LIGHT = {
    "bg": "#f0f0f0",
    "bg_secondary": "#fff",
    "bg_row_even": "#fafafa",
    "bg_row_odd": "#f5f5f5",
    "bg_button": "#e8e8e8",
    "bg_active": "#ddd",
    "border": "#ccc",
    "border_active": "#ccc",
    "text_primary": "#222",
    "text_secondary": "#888",
    "text_hint": "#aaa",
    "text_header": "#666",
    "text_button": "#666",
    "start_bg": "#888",
    "start_text": "#fff",
}

_THEMES = {"dark": _DARK, "light": _LIGHT}


class Theme:
    def __init__(self, name="dark"):
        self._name = name if name in _THEMES else "dark"

    @property
    def name(self):
        return self._name

    def toggle(self):
        self._name = "light" if self._name == "dark" else "dark"

    def _colors(self):
        return _THEMES[self._name]

    def __getattr__(self, key):
        colors = _THEMES.get(self.__dict__.get("_name", "dark"), _DARK)
        if key in colors:
            return colors[key]
        raise AttributeError(f"Theme has no color '{key}'")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_theme.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add ui/theme.py tests/test_theme.py
git commit -m "feat: add theme module with dark/light palettes"
```

---

### Task 2: Rewrite Settings Window — Layout Structure

**Files:**
- Rewrite: `ui/settings_window.py`
- Modify: `main.py`

This is the largest task. It replaces the entire settings window UI with the new compact card layout while keeping all behavior.

- [ ] **Step 1: Update main.py to remove old palette**

Replace `main.py` with:

```python
import sys
import os
import logging

if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

LOG_FILE = os.path.join(APP_DIR, "app.log")
logging.basicConfig(
    filename=LOG_FILE, level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S", encoding="utf-8"
)
log = logging.getLogger("refbot")

from PyQt6.QtWidgets import QApplication
from ui.settings_window import SettingsWindow

if __name__ == "__main__":
    log.info("App started")
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = SettingsWindow()
    window.show()
    sys.exit(app.exec())
```

- [ ] **Step 2: Rewrite settings_window.py — full implementation**

Replace `ui/settings_window.py` with the new compact card layout. This is a full rewrite — the complete file content:

```python
import os
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                              QPushButton, QLabel, QCheckBox, QFileDialog,
                              QSizePolicy, QApplication)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QPainter, QColor, QPen
from core.constants import SUPPORTED_FORMATS, TIMER_PRESETS, SESSION_PRESETS
from core.timer_logic import format_time
from core.class_mode import auto_distribute, groups_to_timers, total_duration, format_group
from core.file_utils import filter_image_files, scan_folder
from core.session import save_session, load_session
from core.models import ImageItem
from ui.theme import Theme


ALL_TIERS = [(30, "30с"), (60, "1м"), (180, "3м"),
             (300, "5м"), (600, "10м"), (900, "15м"),
             (1800, "30м"), (3600, "1ч")]


class ThemeToggleButton(QPushButton):
    """Small circle split dark/light halves."""

    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setFixedSize(16, 16)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("background: transparent; border: none;")

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect().adjusted(1, 1, -1, -1)
        cx = r.center().x()
        # Left half dark, right half light
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#333"))
        p.drawChord(r, 90 * 16, 180 * 16)
        p.setBrush(QColor("#ccc"))
        p.drawChord(r, 270 * 16, 180 * 16)
        # Border
        p.setPen(QPen(QColor(self.theme.border_active), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(r)
        p.end()


class SegmentButton(QPushButton):
    """One segment of a two-segment toggle."""
    pass


class PresetButton(QPushButton):
    """Small timer preset button."""
    pass


class TierToggle(QPushButton):
    """Toggleable tier button for session mode."""

    def __init__(self, text, seconds, parent=None):
        super().__init__(text, parent)
        self.seconds = seconds
        self._active = True
        self.setCheckable(True)
        self.setChecked(True)
        self.clicked.connect(self._on_click)

    def _on_click(self):
        self._active = self.isChecked()

    @property
    def active(self):
        return self._active


class SettingsWindow(QMainWindow):
    images_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("RefBot")
        self.setFixedWidth(360)
        self.images = []
        self.viewer = None
        self.editor = None
        self.theme = Theme("dark")

        self._timer_mode = "standard"  # "standard" or "session"
        self._preset_index = 1  # default 5min
        self._session_index = 2  # default 1h
        self._manual_groups = []
        self._class_groups = []

        self._build_ui()
        self._apply_theme()
        self._restore_session()
        self.setAcceptDrops(True)

    # ------------------------------------------------------------------ UI

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(10)

        # 1. Header row: REFBOT + theme toggle
        header_row = QHBoxLayout()
        header_row.addStretch()
        self._title = QLabel("REFBOT")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_row.addWidget(self._title)
        self._theme_btn = ThemeToggleButton(self.theme)
        self._theme_btn.clicked.connect(self._toggle_theme)
        header_row.addStretch()
        header_row.addWidget(self._theme_btn)
        root.addLayout(header_row)

        # 2. Drop zone
        self._drop_zone = QLabel("Перетащите изображения сюда\nили нажмите для выбора")
        self._drop_zone.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._drop_zone.setFixedHeight(70)
        self._drop_zone.setCursor(Qt.CursorShape.PointingHandCursor)
        self._drop_zone.mousePressEvent = lambda e: self._add_files()
        root.addWidget(self._drop_zone)

        # 3. Thumbnail strip + Edit button
        thumb_row = QHBoxLayout()
        thumb_row.setSpacing(2)
        self._thumb_labels = []
        for i in range(9):
            lbl = QLabel()
            lbl.setFixedSize(36, 36)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.hide()
            self._thumb_labels.append(lbl)
            thumb_row.addWidget(lbl)
        self._overflow_label = QLabel()
        self._overflow_label.setFixedSize(36, 36)
        self._overflow_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._overflow_label.hide()
        thumb_row.addWidget(self._overflow_label)
        thumb_row.addStretch()
        self._edit_btn = QPushButton("Edit")
        self._edit_btn.setFixedHeight(24)
        self._edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._edit_btn.clicked.connect(self._open_editor)
        thumb_row.addWidget(self._edit_btn)
        root.addLayout(thumb_row)

        # 4. Timer mode switch
        mode_row = QHBoxLayout()
        mode_row.setSpacing(0)
        self._standard_btn = SegmentButton("Стандартный")
        self._session_btn = SegmentButton("Сеанс")
        self._standard_btn.clicked.connect(lambda: self._set_timer_mode("standard"))
        self._session_btn.clicked.connect(lambda: self._set_timer_mode("session"))
        mode_row.addWidget(self._standard_btn)
        mode_row.addWidget(self._session_btn)
        root.addLayout(mode_row)

        # 5a. Standard mode content
        self._standard_widget = QWidget()
        std_layout = QVBoxLayout(self._standard_widget)
        std_layout.setContentsMargins(0, 4, 0, 0)
        std_layout.setSpacing(8)

        # Timer with arrows
        timer_row = QHBoxLayout()
        timer_row.addStretch()
        self._timer_left = QPushButton("<")
        self._timer_left.setFixedSize(28, 28)
        self._timer_left.clicked.connect(self._prev_preset)
        timer_row.addWidget(self._timer_left)
        self._timer_display = QLabel("5:00")
        self._timer_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        timer_row.addWidget(self._timer_display)
        self._timer_right = QPushButton(">")
        self._timer_right.setFixedSize(28, 28)
        self._timer_right.clicked.connect(self._next_preset)
        timer_row.addWidget(self._timer_right)
        timer_row.addStretch()
        std_layout.addLayout(timer_row)

        # Preset buttons
        preset_row = QHBoxLayout()
        preset_row.addStretch()
        self._preset_buttons = []
        for secs, label in TIMER_PRESETS:
            btn = PresetButton(label.replace(" ", ""))
            btn.setFixedHeight(22)
            btn._secs = secs
            btn.clicked.connect(lambda checked, s=secs: self._select_preset_by_secs(s))
            self._preset_buttons.append(btn)
            preset_row.addWidget(btn)
        preset_row.addStretch()
        std_layout.addLayout(preset_row)

        root.addWidget(self._standard_widget)

        # 5b. Session mode content
        self._session_widget = QWidget()
        ses_layout = QVBoxLayout(self._session_widget)
        ses_layout.setContentsMargins(0, 4, 0, 0)
        ses_layout.setSpacing(8)

        self._session_dur_label = QLabel("ДЛИТЕЛЬНОСТЬ СЕАНСА")
        self._session_dur_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ses_layout.addWidget(self._session_dur_label)

        # Session duration with arrows
        sdur_row = QHBoxLayout()
        sdur_row.addStretch()
        self._ses_left = QPushButton("<")
        self._ses_left.setFixedSize(28, 28)
        self._ses_left.clicked.connect(self._prev_session)
        sdur_row.addWidget(self._ses_left)
        self._ses_display = QLabel("1:00:00")
        self._ses_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sdur_row.addWidget(self._ses_display)
        self._ses_right = QPushButton(">")
        self._ses_right.setFixedSize(28, 28)
        self._ses_right.clicked.connect(self._next_session)
        sdur_row.addWidget(self._ses_right)
        sdur_row.addStretch()
        ses_layout.addLayout(sdur_row)

        self._use_label = QLabel("ИСПОЛЬЗОВАТЬ")
        self._use_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ses_layout.addWidget(self._use_label)

        # Tier toggles
        tier_row = QHBoxLayout()
        tier_row.addStretch()
        self._tier_toggles = []
        for secs, label in ALL_TIERS:
            btn = TierToggle(label, secs)
            btn.setFixedHeight(22)
            self._tier_toggles.append(btn)
            tier_row.addWidget(btn)
        tier_row.addStretch()
        ses_layout.addLayout(tier_row)

        # Auto-distribute button
        auto_row = QHBoxLayout()
        auto_row.addStretch()
        self._auto_btn = QPushButton("Авто-распределение")
        self._auto_btn.clicked.connect(self._auto_distribute)
        auto_row.addWidget(self._auto_btn)
        auto_row.addStretch()
        ses_layout.addLayout(auto_row)

        # Groups result (compact line)
        self._groups_label = QLabel("")
        self._groups_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ses_layout.addWidget(self._groups_label)

        self._session_widget.hide()
        root.addWidget(self._session_widget)

        # 6. Random order checkbox
        random_row = QHBoxLayout()
        random_row.addStretch()
        self._random_cb = QCheckBox("Случайный порядок")
        random_row.addWidget(self._random_cb)
        random_row.addStretch()
        root.addLayout(random_row)

        # Spacer
        root.addStretch()

        # 7. Summary line
        self._summary = QLabel("")
        self._summary.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._summary)

        # 8. Always-on-top checkbox
        self._topmost_cb = QCheckBox("Поверх всех окон")
        root.addWidget(self._topmost_cb)

        # 9. Start button
        self._start_btn = QPushButton("СТАРТ")
        self._start_btn.setFixedHeight(40)
        self._start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._start_btn.clicked.connect(self._start_slideshow)
        root.addWidget(self._start_btn)

        self._update_timer_display()
        self._update_session_display()
        self._update_mode_buttons()

    # ------------------------------------------------------------------ Theme

    def _apply_theme(self):
        t = self.theme
        self.setStyleSheet(f"background-color: {t.bg}; color: {t.text_primary};")

        self._title.setStyleSheet(
            f"color: {t.text_header}; font-size: 11px; font-weight: normal; "
            f"letter-spacing: 3px;")

        self._drop_zone.setStyleSheet(
            f"background-color: {t.bg_secondary}; border: 1px dashed {t.border_active}; "
            f"color: {t.text_secondary}; font-size: 12px;")

        for lbl in self._thumb_labels:
            lbl.setStyleSheet(f"background-color: {t.bg_row_even};")
        self._overflow_label.setStyleSheet(
            f"background-color: {t.bg_row_even}; color: {t.text_secondary}; font-size: 10px;")

        edit_s = (f"background-color: {t.bg_button}; color: {t.text_button}; "
                  f"border: 1px solid {t.border}; font-size: 9px; padding: 3px 6px;")
        self._edit_btn.setStyleSheet(edit_s)

        seg_base = (f"font-size: 11px; border: 1px solid {t.border}; padding: 6px;")
        self._standard_btn.setStyleSheet(seg_base)
        self._session_btn.setStyleSheet(seg_base)
        self._update_mode_buttons()

        arrow_s = (f"background-color: transparent; color: {t.text_secondary}; "
                   f"border: none; font-size: 14px;")
        self._timer_left.setStyleSheet(arrow_s)
        self._timer_right.setStyleSheet(arrow_s)
        self._ses_left.setStyleSheet(arrow_s)
        self._ses_right.setStyleSheet(arrow_s)

        self._timer_display.setStyleSheet(
            f"color: {t.text_primary}; font-size: 30px; font-weight: 300;")
        self._ses_display.setStyleSheet(
            f"color: {t.text_primary}; font-size: 30px; font-weight: 300;")

        label_s = (f"color: {t.text_secondary}; font-size: 9px; "
                   f"letter-spacing: 2px;")
        self._session_dur_label.setStyleSheet(label_s)
        self._use_label.setStyleSheet(label_s)

        self._update_preset_styles()
        self._update_tier_styles()

        auto_s = (f"background-color: {t.bg_button}; color: {t.text_button}; "
                  f"border: 1px solid {t.border}; font-size: 10px; padding: 5px 14px;")
        self._auto_btn.setStyleSheet(auto_s)

        self._groups_label.setStyleSheet(
            f"color: {t.text_secondary}; font-size: 10px;")

        cb_s = f"color: {t.text_secondary}; font-size: 9px;"
        self._random_cb.setStyleSheet(cb_s)
        self._topmost_cb.setStyleSheet(cb_s)

        self._summary.setStyleSheet(
            f"color: {t.text_secondary}; font-size: 11px;")

        self._start_btn.setStyleSheet(
            f"background-color: {t.start_bg}; color: {t.start_text}; "
            f"font-size: 13px; font-weight: 500; letter-spacing: 1px; border: none;")

    def _toggle_theme(self):
        self.theme.toggle()
        self._apply_theme()
        self._theme_btn.update()

    # ------------------------------------------------------------------ Mode

    def _set_timer_mode(self, mode):
        self._timer_mode = mode
        self._standard_widget.setVisible(mode == "standard")
        self._session_widget.setVisible(mode == "session")
        self._update_mode_buttons()
        self._update_summary()

    def _update_mode_buttons(self):
        t = self.theme
        active_s = (f"background-color: {t.bg_active}; color: {t.text_primary}; "
                    f"border: 1px solid {t.border}; font-size: 11px; padding: 6px;")
        inactive_s = (f"background-color: {t.bg}; color: {t.text_secondary}; "
                      f"border: 1px solid {t.border}; font-size: 11px; padding: 6px;")
        if self._timer_mode == "standard":
            self._standard_btn.setStyleSheet(active_s)
            self._session_btn.setStyleSheet(inactive_s)
        else:
            self._standard_btn.setStyleSheet(inactive_s)
            self._session_btn.setStyleSheet(active_s)

    # ------------------------------------------------------------------ Standard timer

    def _prev_preset(self):
        if self._preset_index > 0:
            self._preset_index -= 1
            self._update_timer_display()
            self._update_summary()

    def _next_preset(self):
        if self._preset_index < len(TIMER_PRESETS) - 1:
            self._preset_index += 1
            self._update_timer_display()
            self._update_summary()

    def _select_preset_by_secs(self, secs):
        for i, (s, _) in enumerate(TIMER_PRESETS):
            if s == secs:
                self._preset_index = i
                self._update_timer_display()
                self._update_summary()
                return

    def _update_timer_display(self):
        secs, _ = TIMER_PRESETS[self._preset_index]
        self._timer_display.setText(format_time(secs))
        self._update_preset_styles()

    def _update_preset_styles(self):
        t = self.theme
        current_secs = TIMER_PRESETS[self._preset_index][0]
        for btn in self._preset_buttons:
            if btn._secs == current_secs:
                btn.setStyleSheet(
                    f"background-color: {t.bg_active}; color: {t.text_primary}; "
                    f"border: 1px solid {t.border_active}; font-size: 9px; padding: 3px 8px;")
            else:
                btn.setStyleSheet(
                    f"background-color: {t.bg_button}; color: {t.text_secondary}; "
                    f"border: 1px solid {t.border}; font-size: 9px; padding: 3px 8px;")

    def get_timer_seconds(self):
        return TIMER_PRESETS[self._preset_index][0]

    # ------------------------------------------------------------------ Session timer

    def _prev_session(self):
        if self._session_index > 0:
            self._session_index -= 1
            self._update_session_display()
            if self.images:
                self._auto_distribute()

    def _next_session(self):
        if self._session_index < len(SESSION_PRESETS) - 1:
            self._session_index += 1
            self._update_session_display()
            if self.images:
                self._auto_distribute()

    def _update_session_display(self):
        secs, _ = SESSION_PRESETS[self._session_index]
        self._ses_display.setText(format_time(secs))

    def _get_session_seconds(self):
        return SESSION_PRESETS[self._session_index][0]

    # ------------------------------------------------------------------ Tiers

    def _get_selected_tiers(self):
        tiers = []
        for btn in self._tier_toggles:
            if btn.active:
                tiers.append((btn.seconds, btn.text()))
        return tiers if tiers else None

    def _update_tier_styles(self):
        t = self.theme
        for btn in self._tier_toggles:
            if btn.isChecked():
                btn.setStyleSheet(
                    f"background-color: {t.bg_active}; color: {t.text_primary}; "
                    f"border: 1px solid {t.border_active}; font-size: 9px; padding: 3px 7px;")
            else:
                btn.setStyleSheet(
                    f"background-color: {t.bg_button}; color: {t.text_secondary}; "
                    f"border: 1px solid {t.border}; font-size: 9px; padding: 3px 7px;")

    # ------------------------------------------------------------------ Auto-distribute

    def _auto_distribute(self):
        if not self.images:
            return
        total_secs = self._get_session_seconds()
        manual_time = total_duration(self._manual_groups)
        manual_images = sum(c for c, _ in self._manual_groups)
        remaining_time = max(0, total_secs - manual_time)
        remaining_images = max(0, len(self.images) - manual_images)

        if remaining_images > 0 and remaining_time > 0:
            auto_groups = auto_distribute(remaining_images, remaining_time,
                                          custom_tiers=self._get_selected_tiers())
        else:
            auto_groups = []

        combined = self._manual_groups + auto_groups
        combined.sort(key=lambda g: g[1])
        self._class_groups = combined
        self._update_groups_display()
        self._update_summary()

    def _update_groups_display(self):
        if not self._class_groups:
            self._groups_label.setText("")
            return
        parts = []
        for count, timer in self._class_groups:
            if timer >= 3600:
                t = f"{timer // 3600}ч"
            elif timer >= 60:
                t = f"{timer // 60}м"
            else:
                t = f"{timer}с"
            parts.append(f"{count}x{t}")
        self._groups_label.setText("  ".join(parts))

    # ------------------------------------------------------------------ Summary

    def _update_summary(self):
        n = len(self.images)
        if self._timer_mode == "standard":
            if n == 0:
                self._summary.setText("")
            else:
                total = n * self.get_timer_seconds()
                self._summary.setText(f"{n} изображений / {format_time(total)}")
        else:
            if n == 0:
                self._summary.setText("")
            elif self._class_groups:
                used = sum(c for c, _ in self._class_groups)
                dur = total_duration(self._class_groups)
                ses = self._get_session_seconds()
                self._summary.setText(
                    f"{used} из {n} изображений / {format_time(dur)} из {format_time(ses)}")
            else:
                self._summary.setText(f"{n} изображений")

    # ------------------------------------------------------------------ Thumbnails

    def _update_thumbnails(self):
        from PyQt6.QtGui import QPixmap
        max_thumbs = len(self._thumb_labels)
        n = len(self.images)
        show = min(n, max_thumbs)
        overflow = n - show

        for i in range(max_thumbs):
            if i < show:
                pix = QPixmap(self.images[i].path)
                if not pix.isNull():
                    pix = pix.scaled(36, 36,
                                     Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation)
                    self._thumb_labels[i].setPixmap(pix)
                else:
                    self._thumb_labels[i].setText("?")
                self._thumb_labels[i].show()
            else:
                self._thumb_labels[i].hide()
                self._thumb_labels[i].clear()

        if overflow > 0:
            self._overflow_label.setText(f"+{overflow}")
            self._overflow_label.show()
        else:
            self._overflow_label.hide()

    # ------------------------------------------------------------------ Image management

    def _add_files(self):
        exts = " ".join(f"*{e}" for e in SUPPORTED_FORMATS)
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Выберите файлы", "",
            f"Изображения ({exts});;Все файлы (*)"
        )
        if paths:
            timer = self.get_timer_seconds()
            for p in filter_image_files(paths):
                self.images.append(ImageItem(path=p, timer=timer))
            self._on_images_changed()

    def _add_folder(self, folder):
        timer = self.get_timer_seconds()
        for p in scan_folder(folder):
            self.images.append(ImageItem(path=p, timer=timer))
        self._on_images_changed()

    def _on_images_changed(self):
        self._update_thumbnails()
        self._update_summary()
        self.images_changed.emit()
        if self.editor and self.editor.isVisible():
            self.editor.refresh(self.images)

    def _open_editor(self):
        from ui.image_editor_window import ImageEditorWindow
        if self.editor is None or not self.editor.isVisible():
            self.editor = ImageEditorWindow(self.images, self.theme, parent=self)
            self.editor.images_updated.connect(self._on_editor_update)
            self.editor.show()

    def _on_editor_update(self, images):
        self.images = images
        self._update_thumbnails()
        self._update_summary()

    # ------------------------------------------------------------------ Drag and drop

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        paths = [u.toLocalFile() for u in urls]
        timer = self.get_timer_seconds()
        added = 0
        for p in paths:
            if os.path.isdir(p):
                for fp in scan_folder(p):
                    self.images.append(ImageItem(path=fp, timer=timer))
                    added += 1
            elif os.path.isfile(p) and os.path.splitext(p)[1].lower() in SUPPORTED_FORMATS:
                self.images.append(ImageItem(path=p, timer=timer))
                added += 1
        if added:
            self._on_images_changed()
        event.acceptProposedAction()

    # ------------------------------------------------------------------ Slideshow

    def _start_slideshow(self):
        if not self.images:
            return

        show_images = self.images
        if self._timer_mode == "session" and self._class_groups:
            timers = groups_to_timers(self._class_groups)
            show_images = []
            for i, img in enumerate(self.images):
                if i < len(timers):
                    img.timer = timers[i]
                    show_images.append(img)

        settings = {
            "order": "random" if self._random_cb.isChecked() else "sequential",
            "topmost": self._topmost_cb.isChecked(),
        }
        from ui.viewer_window import ViewerWindow
        self.viewer = ViewerWindow(show_images, settings, on_close=self._on_viewer_closed)
        self.viewer.show()
        self.hide()

    def _on_viewer_closed(self):
        self.viewer = None
        self.show()

    # ------------------------------------------------------------------ Session save/restore

    def _restore_session(self):
        data = load_session()
        if not data:
            return
        images_data = data.get("images", [])
        self.images = [ImageItem.from_dict(d) for d in images_data]
        self.images = [img for img in self.images if os.path.isfile(img.path)]

        # Timer preset
        timer_secs = data.get("timer_seconds", 300)
        for i, (s, _) in enumerate(TIMER_PRESETS):
            if s == timer_secs:
                self._preset_index = i
                break

        # Timer mode
        if data.get("timer_mode") == "class":
            self._timer_mode = "session"

        # Session preset
        session_secs = data.get("session_seconds")
        if session_secs:
            for i, (s, _) in enumerate(SESSION_PRESETS):
                if s == session_secs:
                    self._session_index = i
                    break

        self._random_cb.setChecked(data.get("random_order", False))
        self._topmost_cb.setChecked(data.get("topmost", False))

        # Theme
        theme_name = data.get("theme", "dark")
        if theme_name != self.theme.name:
            self.theme.toggle()
            self._apply_theme()

        self._update_timer_display()
        self._update_session_display()
        self._set_timer_mode(self._timer_mode)
        self._update_thumbnails()
        self._update_summary()

    def _save_session(self):
        data = {
            "images": [img.to_dict() for img in self.images],
            "timer_seconds": self.get_timer_seconds(),
            "timer_mode": "class" if self._timer_mode == "session" else "standard",
            "session_seconds": self._get_session_seconds(),
            "random_order": self._random_cb.isChecked(),
            "topmost": self._topmost_cb.isChecked(),
            "theme": self.theme.name,
        }
        save_session(data)

    # ------------------------------------------------------------------ Close

    def closeEvent(self, event):
        if self.viewer is not None and self.viewer.isVisible():
            event.ignore()
            self.hide()
        else:
            self._save_session()
            event.accept()
```

- [ ] **Step 3: Run the app to verify it launches**

Run: `python main.py`
Expected: Window opens with new compact layout, dark theme. Close it.

- [ ] **Step 4: Commit**

```bash
git add main.py ui/settings_window.py
git commit -m "feat: rewrite settings window with compact card layout and theme support"
```

---

### Task 3: Image Editor Window

**Files:**
- Create: `ui/image_editor_window.py`

- [ ] **Step 1: Create image editor window**

Create `ui/image_editor_window.py`:

```python
import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QLabel, QListWidget, QListWidgetItem, QFileDialog,
                              QAbstractItemView)
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from core.constants import SUPPORTED_FORMATS
from core.file_utils import filter_image_files, scan_folder
from core.models import ImageItem
from core.timer_logic import format_time


class ImageEditorWindow(QWidget):
    images_updated = pyqtSignal(list)

    def __init__(self, images, theme, parent=None):
        super().__init__()
        self.images = list(images)  # work on a copy
        self.theme = theme
        self._parent = parent
        self.setWindowTitle("Изображения")
        self.setMinimumSize(340, 400)

        self._build_ui()
        self._apply_theme()
        self._rebuild_list()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 8, 12, 8)
        root.setSpacing(8)

        # Header
        header = QHBoxLayout()
        self._count_label = QLabel("")
        header.addWidget(self._count_label)
        header.addStretch()
        close_btn = QPushButton("x")
        close_btn.setFixedSize(20, 20)
        close_btn.clicked.connect(self.close)
        header.addWidget(close_btn)
        root.addLayout(header)

        # Toolbar
        toolbar = QHBoxLayout()
        self._add_files_btn = QPushButton("+ Файлы")
        self._add_files_btn.clicked.connect(self._add_files)
        toolbar.addWidget(self._add_files_btn)
        self._add_folder_btn = QPushButton("+ Папка")
        self._add_folder_btn.clicked.connect(self._add_folder)
        toolbar.addWidget(self._add_folder_btn)
        toolbar.addStretch()
        self._clear_btn = QPushButton("Очистить")
        self._clear_btn.clicked.connect(self._clear)
        toolbar.addWidget(self._clear_btn)
        root.addLayout(toolbar)

        # File list
        self._list = QListWidget()
        self._list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self._list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self._list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self._list.setIconSize(QSize(28, 28))
        self._list.model().rowsMoved.connect(self._on_reorder)
        root.addWidget(self._list)

        # Bottom controls
        bottom = QHBoxLayout()
        bottom.addStretch()
        self._up_btn = QPushButton("^")
        self._up_btn.setFixedSize(30, 24)
        self._up_btn.clicked.connect(self._move_up)
        bottom.addWidget(self._up_btn)
        self._down_btn = QPushButton("v")
        self._down_btn.setFixedSize(30, 24)
        self._down_btn.clicked.connect(self._move_down)
        bottom.addWidget(self._down_btn)
        bottom.addStretch()
        root.addLayout(bottom)

    def _apply_theme(self):
        t = self.theme
        self.setStyleSheet(f"background-color: {t.bg}; color: {t.text_primary};")

        self._count_label.setStyleSheet(f"color: {t.text_secondary}; font-size: 11px;")

        btn_s = (f"background-color: {t.bg_button}; color: {t.text_button}; "
                 f"border: 1px solid {t.border}; font-size: 9px; padding: 3px 8px;")
        for btn in [self._add_files_btn, self._add_folder_btn, self._clear_btn,
                    self._up_btn, self._down_btn]:
            btn.setStyleSheet(btn_s)

        self._list.setStyleSheet(
            f"QListWidget {{ background-color: {t.bg_secondary}; border: none; }}"
            f"QListWidget::item {{ padding: 3px; }}"
            f"QListWidget::item:selected {{ background-color: {t.bg_active}; }}")

    def _rebuild_list(self):
        self._list.clear()
        for i, img in enumerate(self.images):
            name = os.path.basename(img.path)
            timer_str = format_time(img.timer)
            text = f"{i + 1}.  {name}    {timer_str}"
            item = QListWidgetItem(text)
            pix = QPixmap(img.path)
            if not pix.isNull():
                pix = pix.scaled(28, 28,
                                 Qt.AspectRatioMode.KeepAspectRatio,
                                 Qt.TransformationMode.SmoothTransformation)
                item.setIcon(QIcon(pix))
            item.setData(Qt.ItemDataRole.UserRole, i)
            self._list.addItem(item)
        self._count_label.setText(f"Изображения — {len(self.images)}")

    def refresh(self, images):
        self.images = list(images)
        self._rebuild_list()

    def _emit(self):
        self.images_updated.emit(self.images)

    # ------------------------------------------------------------------ Actions

    def _add_files(self):
        exts = " ".join(f"*{e}" for e in SUPPORTED_FORMATS)
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Выберите файлы", "",
            f"Изображения ({exts});;Все файлы (*)")
        if paths:
            for p in filter_image_files(paths):
                self.images.append(ImageItem(path=p, timer=300))
            self._rebuild_list()
            self._emit()

    def _add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку")
        if folder:
            for p in scan_folder(folder):
                self.images.append(ImageItem(path=p, timer=300))
            self._rebuild_list()
            self._emit()

    def _clear(self):
        self.images = []
        self._rebuild_list()
        self._emit()

    def _move_up(self):
        row = self._list.currentRow()
        if row > 0:
            self.images[row], self.images[row - 1] = self.images[row - 1], self.images[row]
            self._rebuild_list()
            self._list.setCurrentRow(row - 1)
            self._emit()

    def _move_down(self):
        row = self._list.currentRow()
        if 0 <= row < len(self.images) - 1:
            self.images[row], self.images[row + 1] = self.images[row + 1], self.images[row]
            self._rebuild_list()
            self._list.setCurrentRow(row + 1)
            self._emit()

    def _on_reorder(self):
        new_order = []
        for i in range(self._list.count()):
            item = self._list.item(i)
            orig_idx = item.data(Qt.ItemDataRole.UserRole)
            if orig_idx is not None and orig_idx < len(self.images):
                new_order.append(self.images[orig_idx])
        if new_order:
            self.images = new_order
            self._rebuild_list()
            self._emit()

    def _delete_selected(self):
        rows = sorted([idx.row() for idx in self._list.selectedIndexes()], reverse=True)
        for row in rows:
            if 0 <= row < len(self.images):
                self.images.pop(row)
        self._rebuild_list()
        self._emit()
```

- [ ] **Step 2: Run the app and test the editor**

Run: `python main.py`
Expected: Click "Edit" button — editor window opens. Add files, reorder, close. Main window updates.

- [ ] **Step 3: Commit**

```bash
git add ui/image_editor_window.py
git commit -m "feat: add image editor window with drag-and-drop and up/down controls"
```

---

### Task 4: Wire Up Tier Toggle Styling and Delete in Editor

**Files:**
- Modify: `ui/settings_window.py`
- Modify: `ui/image_editor_window.py`

- [ ] **Step 1: Add tier toggle style updates on click**

In `ui/settings_window.py`, add to each `TierToggle`'s click handler a call to update styles. In `_build_ui`, after creating tier toggles, connect their `clicked` signal:

In the tier toggle creation loop, add after `self._tier_toggles.append(btn)`:
```python
            btn.clicked.connect(self._update_tier_styles)
```

- [ ] **Step 2: Add delete key support in image editor**

In `ui/image_editor_window.py`, add a `keyPressEvent` to the `ImageEditorWindow` class:

```python
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            self._delete_selected()
        else:
            super().keyPressEvent(event)
```

Also add an "x" delete button in the toolbar row, between the spacer and clear button:

In `_build_ui`, before `self._clear_btn`:
```python
        self._del_btn = QPushButton("x")
        self._del_btn.clicked.connect(self._delete_selected)
        toolbar.addWidget(self._del_btn)
```

And add it to the theme styling list in `_apply_theme`.

- [ ] **Step 3: Run the app and test**

Run: `python main.py`
Expected: Tier toggles change style on click. Delete key and "x" button remove selected images in editor.

- [ ] **Step 4: Commit**

```bash
git add ui/settings_window.py ui/image_editor_window.py
git commit -m "fix: tier toggle styling on click, delete support in editor"
```

---

### Task 5: Run All Tests and Final Verification

**Files:** none (testing only)

- [ ] **Step 1: Run all existing tests**

Run: `python -m pytest tests/ -v`
Expected: All 57+ tests pass (core logic unchanged).

- [ ] **Step 2: Manual smoke test**

Run: `python main.py`

Test checklist:
1. Window opens in dark theme
2. Click theme toggle — switches to light, click again — back to dark
3. Drag image files onto drop zone — thumbnails appear
4. Click "Edit" — editor opens with file list
5. Reorder with drag-and-drop and up/down buttons
6. Delete with "x" button and Delete key
7. Close editor — main window reflects changes
8. Switch to "Сеанс" mode — session controls appear
9. Change duration with arrows — works
10. Toggle tiers on/off — style updates
11. Click "Авто-распределение" — groups line appears
12. Summary shows correct counts
13. Check "Случайный порядок" and "Поверх всех окон"
14. Click "Старт" — viewer opens
15. Close viewer — settings window returns
16. Close and reopen — session restored including theme

- [ ] **Step 3: Commit any fixes if needed**

- [ ] **Step 4: Build exe**

```bash
python -m PyInstaller --noconfirm --onefile --windowed --name RefBot main.py
```

Expected: `dist/RefBot.exe` built successfully.

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "chore: verified UI redesign, rebuilt exe"
```
