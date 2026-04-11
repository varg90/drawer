# Sketchbook Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign Drawer's visual identity from neutral grey to warm "Sketchbook / Artist's Studio" aesthetic with Lora + Lexend fonts, rounded corners, background gradients, and reorganized editor controls.

**Architecture:** Update the existing Theme/Scales/Widgets layer, add QPainter-based rounded window rendering, and reorganize editor panel controls. All changes flow through the centralized theme system. Font loading added at app startup.

**Tech Stack:** Python, PyQt6, QPainter, QFontDatabase, existing CustomTkinter replaced by PyQt6 (already done)

**Spec:** `docs/superpowers/specs/2026-04-11-sketchbook-redesign-design.md`
**Visual mockup:** `redesign_concept.html` (open in browser for reference)

---

### Task 1: Add Font Files

**Files:**
- Create: `fonts/Lora-Bold.ttf`
- Create: `fonts/Lexend-Regular.ttf`
- Create: `fonts/Lexend-Medium.ttf`
- Modify: `main.py`

- [ ] **Step 1: Create fonts directory and download font files**

```bash
mkdir -p fonts
# Download Lora Bold
python -c "import urllib.request; urllib.request.urlretrieve('https://github.com/google/fonts/raw/main/ofl/lora/Lora%5Bwght%5D.ttf', 'fonts/Lora[wght].ttf')"
# Download Lexend
python -c "import urllib.request; urllib.request.urlretrieve('https://github.com/google/fonts/raw/main/ofl/lexend/Lexend%5Bwght%5D.ttf', 'fonts/Lexend[wght].ttf')"
```

Note: Variable font files (`.ttf` with `[wght]`) contain all weights. If variable fonts cause issues with Qt, download individual static files from `fonts/google/fonts/ofl/lora/static/` and `ofl/lexend/static/` instead.

- [ ] **Step 2: Add font loading to main.py**

Add after `app = QApplication(sys.argv)` (line 23):

```python
from PyQt6.QtGui import QFontDatabase
import glob

fonts_dir = os.path.join(APP_DIR, "fonts")
for font_file in glob.glob(os.path.join(fonts_dir, "*.ttf")):
    result = QFontDatabase.addApplicationFont(font_file)
    if result == -1:
        logging.warning("Failed to load font: %s", font_file)
```

- [ ] **Step 3: Verify fonts load**

```bash
python -c "
import sys, os, glob
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFontDatabase
app = QApplication(sys.argv)
for f in glob.glob('fonts/*.ttf'):
    r = QFontDatabase.addApplicationFont(f)
    fam = QFontDatabase.applicationFontFamilies(r)
    print(f'{f}: {fam}')
"
```

Expected: Lists font families like `['Lora']` and `['Lexend']`.

- [ ] **Step 4: Commit**

```bash
git add fonts/ main.py
git commit -m "feat: add Lora + Lexend fonts for Sketchbook redesign"
```

---

### Task 2: Update Theme Colors

**Files:**
- Modify: `ui/theme.py`
- Modify: `tests/test_theme.py`

- [ ] **Step 1: Replace color dictionaries in theme.py**

Replace `_DARK_BASE` (lines 6-18) with:

```python
_DARK_BASE = {
    "bg": "#16120e",
    "bg_secondary": "#120e0a",
    "bg_row_even": "#1a1610",
    "bg_row_odd": "#1e1a14",
    "bg_button": "#16120e",
    "border": "#120e0a",
    "text_primary": "#ccc0ae",
    "text_secondary": "#7a6b5a",
    "text_hint": "#4a3e32",
    "start_text": "#16120e",
    "warning": "#cc5555",
}
```

Replace `_LIGHT_BASE` (lines 20-32) with:

```python
_LIGHT_BASE = {
    "bg": "#d8ccb8",
    "bg_secondary": "#e0d6c4",
    "bg_row_even": "#d4c8b4",
    "bg_row_odd": "#d0c4ae",
    "bg_button": "#d8ccb8",
    "border": "#c0b4a0",
    "text_primary": "#2a2018",
    "text_secondary": "#5a5248",
    "text_hint": "#a0947e",
    "start_text": "#d8ccb8",
    "warning": "#cc4444",
}
```

- [ ] **Step 2: Update accent color derivations**

Replace `_accent_colors` function (lines 72-89) with:

```python
def _accent_colors(accent, mode):
    """Derive accent-dependent colors from a single accent hex."""
    if mode == "dark":
        return {
            "bg_active": _mix("#1a1610", accent, 0.15),
            "bg_panel": "#120e0a",
            "border_active": accent,
            "text_header": "#6b5e4e",
            "text_button": _mix(accent, "#ccc0ae", 0.4),
            "start_bg": accent,
        }
    else:
        return {
            "bg_active": _lighten(accent, 0.65),
            "bg_panel": "#c8bca4",
            "border_active": accent,
            "text_header": "#7a6e5e",
            "text_button": _darken(accent, 0.15),
            "start_bg": accent,
        }
```

- [ ] **Step 3: Run existing theme tests**

```bash
python -m pytest tests/test_theme.py -v
```

Fix any assertions that check specific color values. Tests should verify:
- Theme object creates without error
- Toggle switches between dark/light
- Accent color setter works
- Color attributes are accessible

- [ ] **Step 4: Commit**

```bash
git add ui/theme.py tests/test_theme.py
git commit -m "feat: update theme to Ink & Coffee / Craft Paper palette"
```

---

### Task 3: Update Scales

**Files:**
- Modify: `ui/scales.py`
- Modify: `tests/test_scales.py`

- [ ] **Step 1: Update scale constants**

```python
class S:
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

    # Start button
    START_ICON_RATIO = 0.75
    START_RADIUS_RATIO = 0.19  # 10px / 52px

    # Title
    TITLE_W = 105

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

    # Editor toolbar buttons
    EDITOR_BTN = 15
```

- [ ] **Step 2: Run scales tests, fix assertions**

```bash
python -m pytest tests/test_scales.py -v
```

- [ ] **Step 3: Commit**

```bash
git add ui/scales.py tests/test_scales.py
git commit -m "feat: update scales for Sketchbook redesign"
```

---

### Task 4: Rounded Window Painting

**Files:**
- Create: `ui/rounded_window.py`
- Modify: `ui/settings_window.py`
- Modify: `ui/image_editor_window.py`
- Modify: `ui/snap.py`

- [ ] **Step 1: Create rounded window mixin**

Create `ui/rounded_window.py`:

```python
"""Mixin for painting frameless windows with rounded corners."""

from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QPainterPath, QColor
from PyQt6.QtWidgets import QWidget

from ui.scales import S


class RoundedWindowMixin:
    """Adds rounded-corner painting to frameless windows.

    Call rounded_init() after super().__init__().
    Override corner_radii() to control which corners are rounded.
    """

    def rounded_init(self):
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def corner_radii(self):
        """Return (top_left, top_right, bottom_right, bottom_left) radii."""
        r = S.WINDOW_RADIUS
        return (r, r, r, r)

    def _bg_color(self):
        """Override to return the window background QColor."""
        return QColor("#16120e")

    def _paint_rounded(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        tl, tr, br, bl = self.corner_radii()
        rect = QRectF(self.rect())
        path = QPainterPath()
        if tl == tr == br == bl:
            path.addRoundedRect(rect, tl, tl)
        else:
            # Manually build path with per-corner radii
            path.moveTo(rect.left() + tl, rect.top())
            path.lineTo(rect.right() - tr, rect.top())
            if tr:
                path.arcTo(rect.right() - 2*tr, rect.top(), 2*tr, 2*tr, 90, -90)
            else:
                path.lineTo(rect.right(), rect.top())
            path.lineTo(rect.right(), rect.bottom() - br)
            if br:
                path.arcTo(rect.right() - 2*br, rect.bottom() - 2*br, 2*br, 2*br, 0, -90)
            else:
                path.lineTo(rect.right(), rect.bottom())
            path.lineTo(rect.left() + bl, rect.bottom())
            if bl:
                path.arcTo(rect.left(), rect.bottom() - 2*bl, 2*bl, 2*bl, -90, -90)
            else:
                path.lineTo(rect.left(), rect.bottom())
            path.lineTo(rect.left(), rect.top() + tl)
            if tl:
                path.arcTo(rect.left(), rect.top(), 2*tl, 2*tl, 180, -90)
            else:
                path.lineTo(rect.left(), rect.top())
            path.closeSubpath()
        painter.fillPath(path, self._bg_color())
        painter.end()
```

- [ ] **Step 2: Integrate into SettingsWindow**

In `ui/settings_window.py`, add import and mixin:

```python
from ui.rounded_window import RoundedWindowMixin
```

Change class declaration:
```python
class SettingsWindow(QMainWindow, SnapMixin, RoundedWindowMixin):
```

In `__init__`, after `self.snap_init()`:
```python
self.rounded_init()
```

Add corner_radii method:
```python
def corner_radii(self):
    r = S.WINDOW_RADIUS
    if self._snap_parent or self._snap_children:
        return (r, 0, 0, r)  # rounded left only when snapped
    return (r, r, r, r)
```

Add `_bg_color` and `paintEvent`:
```python
def _bg_color(self):
    return QColor(self.theme.bg)

def paintEvent(self, event):
    self._paint_rounded(event)
```

Remove any `background-color` from the main widget stylesheet in `_apply_theme()` since paintEvent handles it now.

- [ ] **Step 3: Integrate into ImageEditorWindow**

Same pattern in `ui/image_editor_window.py`:

```python
from ui.rounded_window import RoundedWindowMixin

class ImageEditorWindow(QWidget, SnapMixin, RoundedWindowMixin):
```

```python
def corner_radii(self):
    r = S.WINDOW_RADIUS
    if self._snap_parent:
        return (0, r, r, 0)  # rounded right only when snapped to main
    return (r, r, r, r)

def _bg_color(self):
    return QColor(self.theme.bg_secondary)

def paintEvent(self, event):
    self._paint_rounded(event)
```

- [ ] **Step 4: Test visually**

```bash
python main.py
```

Verify: both windows show rounded corners. Snap them together — main rounds left, editor rounds right. Detach — both fully rounded.

- [ ] **Step 5: Commit**

```bash
git add ui/rounded_window.py ui/settings_window.py ui/image_editor_window.py
git commit -m "feat: add rounded window corners via QPainter"
```

---

### Task 5: Update Widgets Layer

**Files:**
- Modify: `ui/widgets.py`
- Modify: `tests/test_widgets.py`

- [ ] **Step 1: Update make_start_btn for new size and font**

Replace `make_start_btn` (lines 79-92) with:

```python
def make_start_btn(theme, parent=None):
    size = S.ICON_START  # 52
    icon_size = int(size * S.START_ICON_RATIO)
    radius = int(size * S.START_RADIUS_RATIO)  # 10
    btn = IconButton(parent=parent)
    btn.setFixedSize(size, size)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    btn.setIcon(
        qta.icon(Icons.START, color=theme.start_text),
        icon_size,
    )
    btn.setStyleSheet(
        f"background-color: {theme.start_bg}; "
        f"border-radius: {radius}px; border: none;"
    )
    return btn
```

- [ ] **Step 2: Update timer_btn_style for rounded corners and font**

Replace `timer_btn_style` (lines 148-158) with:

```python
def timer_btn_style(active, theme):
    if active:
        bg, fg, fw = theme.start_bg, theme.start_text, 600
    else:
        bg, fg, fw = theme.bg_button, theme.text_secondary, 500
    return (
        f"background-color: {bg}; color: {fg}; "
        f"font-family: 'Lexend'; font-size: {S.FONT_BUTTON}px; font-weight: {fw}; "
        f"padding: {S.TIMER_BTN_PADDING_V}px {S.TIMER_BTN_PADDING_H}px; "
        f"border-radius: {S.TIMER_BTN_RADIUS}px; border: none;"
    )
```

- [ ] **Step 3: Update TitleLabel for Lora font**

In `TitleLabel.__init__` (line 107), change font setup:

```python
font = QFont("Lora")
font.setPixelSize(px)
font.setWeight(QFont.Weight(weight))
if letter_spacing:
    font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, letter_spacing)
self.setFont(font)
```

- [ ] **Step 4: Run widget tests, fix assertions**

```bash
python -m pytest tests/test_widgets.py -v
```

- [ ] **Step 5: Commit**

```bash
git add ui/widgets.py tests/test_widgets.py
git commit -m "feat: update widgets for Lexend/Lora fonts and rounded buttons"
```

---

### Task 6: Main Window Layout

**Files:**
- Modify: `ui/settings_window.py`

- [ ] **Step 1: Update title and padding**

In `_build_ui()`, update the title creation. Change "DRAWER" to "Drawer":

```python
title = TitleLabel("Drawer", px=S.FONT_TITLE, weight=700,
                   letter_spacing=1.5, fixed_w=S.TITLE_W)
```

Update the main layout margins (find `lay.setContentsMargins`):

```python
lay.setContentsMargins(S.MARGIN, S.MARGIN_TOP, S.MARGIN, S.MARGIN_BOTTOM)
```

- [ ] **Step 2: Add panel widget around TimerPanel**

Wrap the TimerPanel in a panel widget with the inset background. In `_build_ui()`, replace the timer panel addition with:

```python
self._panel = QWidget()
self._panel.setObjectName("insetPanel")
panel_lay = QVBoxLayout(self._panel)
panel_lay.setContentsMargins(S.PANEL_PADDING, S.PANEL_PADDING,
                              S.PANEL_PADDING, S.PANEL_PADDING)
panel_lay.setSpacing(0)
panel_lay.addWidget(self._timer_panel)

# Center panel vertically with stretch above and below
lay.addStretch()
lay.addWidget(self._panel)
lay.addStretch()
```

- [ ] **Step 3: Style the panel in _apply_theme()**

Add panel styling:

```python
self._panel.setStyleSheet(
    f"QWidget#insetPanel {{ "
    f"background-color: {t.bg_panel}; "
    f"border-radius: {S.PANEL_RADIUS}px; "
    f"}}"
)
```

- [ ] **Step 4: Update title color with emboss effect**

In `_apply_theme()`, update the title recolor to use `text_header`:

```python
self._title.recolor(t.text_header)
```

Note: The CSS text-shadow emboss effect from the mockup would need QPainter custom painting on TitleLabel. For v1, just the color change is sufficient. Can add emboss later.

- [ ] **Step 5: Update _apply_theme() stylesheet**

Change the main stylesheet to remove `background-color` (handled by paintEvent now) but keep text color:

```python
self.setStyleSheet(
    f"QMainWindow {{ background: transparent; color: {t.text_primary}; }}"
    f"QWidget {{ font-family: 'Lexend'; }}"
)
```

- [ ] **Step 6: Test visually**

```bash
python main.py
```

Verify: title says "Drawer" in Lora serif, panel has inset background, content centered with air above and below.

- [ ] **Step 7: Commit**

```bash
git add ui/settings_window.py
git commit -m "feat: main window layout with inset panel and Lora title"
```

---

### Task 7: Timer Panel Styling

**Files:**
- Modify: `ui/timer_panel.py`

- [ ] **Step 1: Update mode button styling**

In `_build()` and `set_timer_mode()`, update mode button styles to include border-radius and Lexend font:

```python
active_s = (
    f"background-color: {self.theme.start_bg}; "
    f"color: {self.theme.start_text}; "
    f"font-family: 'Lexend'; font-size: {S.FONT_MODE}px; font-weight: 600; "
    f"border-radius: {S.MODE_BTN_RADIUS}px; border: none;"
)
inactive_s = (
    f"background-color: {self.theme.bg_button}; "
    f"color: {self.theme.text_secondary}; "
    f"font-family: 'Lexend'; font-size: {S.FONT_MODE}px; font-weight: 500; "
    f"border-radius: {S.MODE_BTN_RADIUS}px; border: none;"
)
```

- [ ] **Step 2: Update timer button active state**

In `_update_quick_highlight()` and class tier toggle, active buttons use full accent fill (not left-border). This is already handled by `timer_btn_style()` updated in Task 5.

Verify all calls to `timer_btn_style()` pass the correct active state.

- [ ] **Step 3: Update spacing**

Set the spacing between mode row and timer grid to `S.SPACING_MODE` (6px, reduced from 10px).

- [ ] **Step 4: Test**

```bash
python main.py
```

Toggle between Quick and Class modes. Verify rounded buttons, Lexend font, accent fill on active.

- [ ] **Step 5: Commit**

```bash
git add ui/timer_panel.py
git commit -m "feat: timer panel with rounded buttons and Lexend font"
```

---

### Task 8: Bottom Bar

**Files:**
- Modify: `ui/bottom_bar.py`

- [ ] **Step 1: Update add button size and radius**

Change add button creation to use 26px size with 5px radius:

```python
self._add_btn = make_icon_btn(Icons.PLUS, theme.text_hint, size=26, parent=self)
self._add_btn.setStyleSheet(
    f"background-color: {theme.bg_button}; "
    f"border: 1px solid {theme.border}; "
    f"border-radius: 5px;"
)
```

- [ ] **Step 2: Update label fonts**

Set Lexend font on all labels:

```python
self._groups_label.setStyleSheet(
    f"font-family: 'Lexend'; font-size: {S.FONT_HINT}px; font-weight: 400; "
    f"color: {t.text_secondary};"
)
self._total_label.setStyleSheet(
    f"font-family: 'Lexend'; font-size: {S.FONT_TOTAL}px; font-weight: 500; "
    f"color: {t.text_primary};"
)
self._limit_btn.setStyleSheet(
    f"font-family: 'Lexend'; font-size: 9px; font-weight: 400; "
    f"color: {t.text_hint}; background: transparent; border: none;"
)
```

- [ ] **Step 3: Update start button icon color**

The start button icon color should match window bg (`theme.start_text`). This is already handled by `make_start_btn()` from Task 5.

- [ ] **Step 4: Test**

```bash
python main.py
```

Verify: 52px start button with 10px radius, 26px add button, Lexend on all labels, session limit visible.

- [ ] **Step 5: Commit**

```bash
git add ui/bottom_bar.py
git commit -m "feat: bottom bar with larger start button and Lexend font"
```

---

### Task 9: Editor Window

**Files:**
- Modify: `ui/image_editor_window.py`

- [ ] **Step 1: Update padding to match main window**

Change editor inner padding to match main window:

```python
lay.setContentsMargins(S.MARGIN, S.MARGIN_TOP, S.MARGIN, S.MARGIN_BOTTOM)
```

- [ ] **Step 2: Remove detach button if present**

Verify the toolbar only has: add_files, add_folder, add_url (left) and close (right). Remove any detach/dock button references.

- [ ] **Step 3: Update stylesheet for transparency**

```python
self.setStyleSheet(
    f"background: transparent; color: {t.text_primary}; "
    f"font-family: 'Lexend';"
)
```

- [ ] **Step 4: Test**

```bash
python main.py
```

Open the editor. Verify: headers align with main window, no detach button, rounded corners on right side when snapped.

- [ ] **Step 5: Commit**

```bash
git add ui/image_editor_window.py
git commit -m "feat: editor window padding alignment and cleanup"
```

---

### Task 10: Editor Panel Controls

**Files:**
- Modify: `ui/editor_panel.py`
- Modify: `ui/icons.py`
- Create: `tests/test_pinned_sort.py`

- [ ] **Step 1: Add zoom icons to icons.py**

```python
# Zoom controls (grid view)
ZOOM_IN = "ph.magnifying-glass-plus-bold"
ZOOM_OUT = "ph.magnifying-glass-minus-bold"
```

- [ ] **Step 2: Reorganize bottom controls**

Replace the bottom controls layout (around lines 201-259) with:

```python
# Bottom bar
ctrl = QHBoxLayout()
ctrl.setSpacing(6)
ctrl.setContentsMargins(0, 5, 0, 0)

# Left group: list/grid toggle
self._list_btn = make_icon_btn(Icons.LIST, theme.text_primary, S.EDITOR_BTN, self)
self._grid_btn = make_icon_btn(Icons.GRID, theme.text_secondary, S.EDITOR_BTN, self)

ctrl.addWidget(self._list_btn)
ctrl.addWidget(self._grid_btn)

# Separator
sep1 = QFrame()
sep1.setFrameShape(QFrame.Shape.VLine)
sep1.setFixedHeight(11)
ctrl.addWidget(sep1)

# Zoom +/- (visible in grid mode)
self._zoom_out_btn = make_icon_btn(Icons.ZOOM_OUT, theme.text_hint, S.EDITOR_BTN, self)
self._zoom_in_btn = make_icon_btn(Icons.ZOOM_IN, theme.text_hint, S.EDITOR_BTN, self)
self._zoom_out_btn.setToolTip("Zoom out")
self._zoom_in_btn.setToolTip("Zoom in")

ctrl.addWidget(self._zoom_out_btn)
ctrl.addWidget(self._zoom_in_btn)

# Separator
sep2 = QFrame()
sep2.setFrameShape(QFrame.Shape.VLine)
sep2.setFixedHeight(11)
ctrl.addWidget(sep2)

# Shuffle
self._shuffle_btn = make_icon_btn(Icons.SHUFFLE, theme.text_hint, S.EDITOR_BTN, self)
ctrl.addWidget(self._shuffle_btn)

ctrl.addStretch()

# Right group: cache + clear
self._cache_btn = make_icon_btn(Icons.TRASH, theme.text_secondary, S.EDITOR_BTN, self)
self._cache_size_label = QLabel()
ctrl.addWidget(self._cache_btn)
ctrl.addWidget(self._cache_size_label)

sep3 = QFrame()
sep3.setFrameShape(QFrame.Shape.VLine)
sep3.setFixedHeight(11)
ctrl.addWidget(sep3)

self._clear_btn = make_icon_btn(Icons.ERASER, theme.text_secondary, S.EDITOR_BTN, self)
ctrl.addWidget(self._clear_btn)
```

- [ ] **Step 3: Connect zoom buttons**

```python
ZOOM_STEP = 16

self._zoom_in_btn.clicked.connect(
    lambda: self._zoom_slider.setValue(
        min(self._zoom_slider.value() + ZOOM_STEP, self._zoom_slider.maximum())
    )
)
self._zoom_out_btn.clicked.connect(
    lambda: self._zoom_slider.setValue(
        max(self._zoom_slider.value() - ZOOM_STEP, self._zoom_slider.minimum())
    )
)
```

Keep the existing zoom slider as the internal state holder but hide it. The +/- buttons and Ctrl+scroll both drive the slider value.

- [ ] **Step 4: Add Ctrl+scroll zoom**

In the grid view widget, add wheel event handling:

```python
def wheelEvent(self, event):
    if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
        delta = event.angleDelta().y()
        step = ZOOM_STEP if delta > 0 else -ZOOM_STEP
        self._zoom_slider.setValue(
            max(self._zoom_slider.minimum(),
                min(self._zoom_slider.value() + step, self._zoom_slider.maximum()))
        )
        event.accept()
    else:
        super().wheelEvent(event)
```

- [ ] **Step 5: Write pinned-first sort test**

Create `tests/test_pinned_sort.py`:

```python
def test_pinned_images_sort_first():
    """Pinned images appear before unpinned in the same group."""
    from ui.editor_panel import _sort_group_items

    items = [
        {"path": "a.jpg", "pinned": False},
        {"path": "b.jpg", "pinned": True},
        {"path": "c.jpg", "pinned": False},
        {"path": "d.jpg", "pinned": True},
    ]
    result = _sort_group_items(items)
    assert result[0]["path"] == "b.jpg"
    assert result[1]["path"] == "d.jpg"
    assert result[2]["path"] == "a.jpg"
    assert result[3]["path"] == "c.jpg"


def test_pinned_sort_preserves_order_within_group():
    """Pinned items keep their relative order, as do unpinned."""
    from ui.editor_panel import _sort_group_items

    items = [
        {"path": "1.jpg", "pinned": True},
        {"path": "2.jpg", "pinned": False},
        {"path": "3.jpg", "pinned": True},
    ]
    result = _sort_group_items(items)
    assert [r["path"] for r in result] == ["1.jpg", "3.jpg", "2.jpg"]
```

- [ ] **Step 6: Run test to verify it fails**

```bash
python -m pytest tests/test_pinned_sort.py -v
```

Expected: FAIL — `_sort_group_items` not defined.

- [ ] **Step 7: Implement pinned-first sort**

In `ui/editor_panel.py`, add:

```python
def _sort_group_items(items):
    """Sort items so pinned come first, preserving relative order."""
    pinned = [i for i in items if i.get("pinned")]
    unpinned = [i for i in items if not i.get("pinned")]
    return pinned + unpinned
```

Call this in the grid/list population methods wherever items within a group are iterated.

- [ ] **Step 8: Run test to verify it passes**

```bash
python -m pytest tests/test_pinned_sort.py -v
```

Expected: PASS

- [ ] **Step 9: Add pin icon overlay to grid tiles**

In the grid tile rendering, for pinned images add a small push-pin icon overlay:

```python
if image.get("pinned"):
    pin_icon = qta.icon(Icons.TOPMOST_ON, color=theme.text_secondary)
    pin_pixmap = pin_icon.pixmap(8, 8)
    # Draw in top-right corner of tile
    painter.drawPixmap(tile_rect.right() - 10, tile_rect.top() + 2, pin_pixmap)
```

The exact integration depends on how tiles are rendered (QLabel vs custom widget). Adapt to the existing tile implementation.

- [ ] **Step 10: Commit**

```bash
git add ui/editor_panel.py ui/icons.py tests/test_pinned_sort.py
git commit -m "feat: editor controls reorg, zoom +/-, pinned-first sort"
```

---

### Task 11: Viewer Warm Overlays

**Files:**
- Modify: `ui/viewer_window.py`

- [ ] **Step 1: Update gradient colors**

In the `_GradientOverlay.paintEvent()`, change the gradient color from pure black to warm brown:

```python
# Replace QColor(0, 0, 0, alpha) with:
QColor(18, 14, 10, alpha)
```

This changes both top and bottom gradients to warm brown-tinted.

- [ ] **Step 2: Update timer font to Lora**

In the timer label setup:

```python
font = QFont("Lora")
font.setPixelSize(20)
self._timer_label.setFont(font)
```

- [ ] **Step 3: Update overlay control colors**

Change the white overlay controls to warm cream:

```python
CLR_NORMAL = QColor(204, 192, 174, 255)  # was (255, 255, 255, 255)
CLR_DIM = QColor(204, 192, 174, 100)     # was (255, 255, 255, 100)
CLR_HOVER = QColor(204, 192, 174, 200)   # was (255, 255, 255, 200)
CLR_WARNING = QColor(230, 120, 100, 200)  # was (255, 85, 85, 200)
```

- [ ] **Step 4: Update progress bar colors**

```python
# Track color
self._progress.setStyleSheet(
    f"background: rgba(36, 30, 24, 150);"  # warm dark track
)
# Fill: keep using accent/teal but at reduced opacity
fill_color = f"rgba({t.start_bg_rgb}, 150)"
```

- [ ] **Step 5: Set Lexend on all viewer labels**

```python
font = QFont("Lexend")
font.setPixelSize(13)
self._counter_label.setFont(font)
```

- [ ] **Step 6: Test visually**

```bash
python main.py
```

Load images and start a slideshow. Verify: warm brown gradients (not black), Lora countdown, cream-colored controls.

- [ ] **Step 7: Commit**

```bash
git add ui/viewer_window.py
git commit -m "feat: viewer warm overlays and Lora countdown"
```

---

### Task 12: Background Gradients (Sketchbook Effect)

**Files:**
- Modify: `ui/rounded_window.py`
- Modify: `ui/settings_window.py`
- Modify: `ui/image_editor_window.py`

- [ ] **Step 1: Add gradient support to RoundedWindowMixin**

In `ui/rounded_window.py`, update `_paint_rounded` to support gradients:

```python
from PyQt6.QtGui import QLinearGradient

class RoundedWindowMixin:
    # ... existing code ...

    def _bg_brush(self):
        """Override to return QColor or QLinearGradient for background."""
        return self._bg_color()

    def _paint_rounded(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        tl, tr, br, bl = self.corner_radii()
        rect = QRectF(self.rect())
        path = QPainterPath()
        # ... existing path building code ...
        brush = self._bg_brush()
        if isinstance(brush, QLinearGradient):
            painter.fillPath(path, brush)
        else:
            painter.fillPath(path, brush)
        painter.end()
```

- [ ] **Step 2: Add gradient to SettingsWindow**

```python
def _bg_brush(self):
    if self.theme.name == "dark":
        grad = QLinearGradient(0, 0, self.width(), 0)
        grad.setColorAt(0.0, QColor("#12100c"))
        grad.setColorAt(1.0, QColor("#1c1814"))
        return grad
    return QColor(self.theme.bg)
```

- [ ] **Step 3: Add mirrored gradient to ImageEditorWindow**

```python
def _bg_brush(self):
    if self.theme.name == "dark":
        grad = QLinearGradient(0, 0, self.width(), 0)
        grad.setColorAt(0.0, QColor("#1c1814"))  # lighter at spine (left)
        grad.setColorAt(1.0, QColor("#12100c"))  # darker at outer edge
        return grad
    return QColor(self.theme.bg_secondary)
```

- [ ] **Step 4: Test visually**

```bash
python main.py
```

Open main + editor side by side in dark mode. Verify: gradients create the sketchbook spine effect — lighter where windows meet, darker at outer edges.

- [ ] **Step 5: Run full test suite**

```bash
python -m pytest tests/ -v
```

All tests should pass.

- [ ] **Step 6: Commit**

```bash
git add ui/rounded_window.py ui/settings_window.py ui/image_editor_window.py
git commit -m "feat: sketchbook background gradients on dark theme"
```

---

### Task 13: Final Verification

- [ ] **Step 1: Full visual test**

```bash
python main.py
```

Check all states:
- Dark mode: warm espresso palette, gradient backgrounds, rounded corners
- Light mode: craft paper palette, solid backgrounds, rounded corners
- Snap/detach: corners adjust correctly
- Quick mode: single timer selection with accent fill
- Class mode: multi-tier selection with accent fill
- Editor: grid view with pin icons, zoom +/- buttons, reorganized bottom bar
- Viewer: warm overlays, Lora countdown, all controls
- Theme toggle: smooth transition between dark/light
- Accent picker: accent color applies to all active states

- [ ] **Step 2: Run full test suite**

```bash
python -m pytest tests/ -v
```

- [ ] **Step 3: Commit any remaining fixes**

```bash
git add -A
git commit -m "fix: final adjustments from visual testing"
```
