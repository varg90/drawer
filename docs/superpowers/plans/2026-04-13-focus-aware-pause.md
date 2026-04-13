# Focus-Aware Pause Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Auto-pause Drawer's timer when a user-chosen external drawing app loses focus, with persistent saved-apps management.

**Architecture:** New `core/focus_monitor.py` module handles OS-level foreground window detection (Windows via ctypes, macOS via Cocoa). New `FocusTracker` widget in `ui/focus_tracker.py` replaces the groups label in BottomBar, providing a toggle + cycling app-selector button. The viewer's existing pause mechanism is extended with an `_auto_paused` flag to distinguish focus-triggered pauses from manual ones.

**Tech Stack:** PyQt6, ctypes (Windows: user32.dll, kernel32.dll, psapi.dll; macOS: AppKit/Cocoa via objc runtime)

---

### Task 1: Core focus monitor — foreground window detection

**Files:**
- Create: `core/focus_monitor.py`
- Create: `tests/test_focus_monitor.py`

- [ ] **Step 1: Write failing tests for focus monitor**

```python
# tests/test_focus_monitor.py
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.focus_monitor import get_foreground_app, list_window_apps


def test_get_foreground_app_returns_string_or_none():
    """get_foreground_app() returns a non-empty string or None."""
    result = get_foreground_app()
    assert result is None or (isinstance(result, str) and len(result) > 0)


def test_list_window_apps_returns_list_of_strings():
    """list_window_apps() returns a list of unique app name strings."""
    result = list_window_apps()
    assert isinstance(result, list)
    for name in result:
        assert isinstance(name, str)
        assert len(name) > 0


def test_list_window_apps_no_duplicates():
    """list_window_apps() should not contain duplicate entries."""
    result = list_window_apps()
    assert len(result) == len(set(result))


def test_get_foreground_app_in_list():
    """The foreground app should appear in the running apps list."""
    fg = get_foreground_app()
    if fg is None:
        return  # headless CI
    apps = list_window_apps()
    assert fg in apps
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_focus_monitor.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.focus_monitor'`

- [ ] **Step 3: Implement focus monitor**

```python
# core/focus_monitor.py
"""Detect foreground window and enumerate running windowed apps.

Windows: ctypes calls to user32/kernel32/psapi.
macOS: Cocoa NSWorkspace via objc runtime.
"""
import sys


def get_foreground_app():
    """Return the process name of the currently focused window, or None."""
    if sys.platform == "win32":
        return _win_foreground()
    if sys.platform == "darwin":
        return _mac_foreground()
    return None


def list_window_apps():
    """Return sorted list of unique app names with visible windows."""
    if sys.platform == "win32":
        return _win_list_apps()
    if sys.platform == "darwin":
        return _mac_list_apps()
    return []


# ------------------------------------------------------------------ Windows

def _win_get_process_name(hwnd):
    """Get process executable name from a window handle."""
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if not pid.value:
        return None

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False,
                                  pid.value)
    if not handle:
        return None
    try:
        buf = ctypes.create_unicode_buffer(260)
        size = wintypes.DWORD(260)
        kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size))
        path = buf.value
        if not path:
            return None
        # Extract filename without extension: "C:\...\Photoshop.exe" -> "Photoshop"
        import os
        return os.path.splitext(os.path.basename(path))[0]
    finally:
        kernel32.CloseHandle(handle)


def _win_foreground():
    """Return the process name of the foreground window on Windows."""
    import ctypes
    hwnd = ctypes.windll.user32.GetForegroundWindow()
    if not hwnd:
        return None
    return _win_get_process_name(hwnd)


def _win_list_apps():
    """Enumerate visible top-level windows and return unique process names."""
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    names = set()

    # Filter out system processes
    _SKIP = {"explorer", "SearchHost", "SearchUI", "ShellExperienceHost",
             "StartMenuExperienceHost", "TextInputHost", "SystemSettings",
             "ApplicationFrameHost", "LockApp", "LogiOverlay"}

    def _enum_callback(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True
        name = _win_get_process_name(hwnd)
        if name and name not in _SKIP:
            names.add(name)
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND,
                                      wintypes.LPARAM)
    user32.EnumWindows(WNDENUMPROC(_enum_callback), 0)
    return sorted(names)


# ------------------------------------------------------------------ macOS

def _mac_foreground():
    """Return the process name of the foreground app on macOS."""
    try:
        import ctypes
        import ctypes.util

        objc = ctypes.cdll.LoadLibrary(ctypes.util.find_library("objc"))
        objc.objc_msgSend.restype = ctypes.c_void_p
        objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        objc.sel_registerName.restype = ctypes.c_void_p
        objc.objc_getClass.restype = ctypes.c_void_p

        def sel(name):
            return objc.sel_registerName(name.encode())

        def msg(obj, selector):
            return objc.objc_msgSend(obj, sel(selector))

        NSWorkspace = objc.objc_getClass(b"NSWorkspace")
        ws = msg(NSWorkspace, "sharedWorkspace")
        app = msg(ws, "frontmostApplication")
        name_ns = msg(app, "localizedName")

        # Convert NSString to Python string
        CoreFoundation = ctypes.cdll.LoadLibrary(ctypes.util.find_library(
            "CoreFoundation"))
        CoreFoundation.CFStringGetCStringPtr.restype = ctypes.c_char_p
        CoreFoundation.CFStringGetCStringPtr.argtypes = [
            ctypes.c_void_p, ctypes.c_uint32]
        raw = CoreFoundation.CFStringGetCStringPtr(name_ns, 0)
        return raw.decode("utf-8") if raw else None
    except Exception:
        return None


def _mac_list_apps():
    """List running apps with visible windows on macOS."""
    try:
        import ctypes
        import ctypes.util

        objc = ctypes.cdll.LoadLibrary(ctypes.util.find_library("objc"))
        objc.objc_msgSend.restype = ctypes.c_void_p
        objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        objc.sel_registerName.restype = ctypes.c_void_p
        objc.objc_getClass.restype = ctypes.c_void_p

        CoreFoundation = ctypes.cdll.LoadLibrary(ctypes.util.find_library(
            "CoreFoundation"))
        CoreFoundation.CFStringGetCStringPtr.restype = ctypes.c_char_p
        CoreFoundation.CFStringGetCStringPtr.argtypes = [
            ctypes.c_void_p, ctypes.c_uint32]

        def sel(name):
            return objc.sel_registerName(name.encode())

        def msg(obj, selector):
            return objc.objc_msgSend(obj, sel(selector))

        # NSRunningApplication activation policy: 0 = regular (has UI)
        msg_int = ctypes.CFUNCTYPE(ctypes.c_long, ctypes.c_void_p,
                                   ctypes.c_void_p)

        NSWorkspace = objc.objc_getClass(b"NSWorkspace")
        ws = msg(NSWorkspace, "sharedWorkspace")
        apps = msg(ws, "runningApplications")
        count = msg_int(objc.objc_msgSend)(apps, sel("count"))

        msg_at = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p,
                                  ctypes.c_void_p, ctypes.c_ulong)
        names = set()
        for i in range(count):
            app = msg_at(objc.objc_msgSend)(apps, sel("objectAtIndex:"), i)
            policy = msg_int(objc.objc_msgSend)(app, sel("activationPolicy"))
            if policy != 0:
                continue
            name_ns = msg(app, "localizedName")
            if not name_ns:
                continue
            raw = CoreFoundation.CFStringGetCStringPtr(name_ns, 0)
            if raw:
                name = raw.decode("utf-8")
                if name and name not in ("Finder", "Dock"):
                    names.add(name)
        return sorted(names)
    except Exception:
        return []
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_focus_monitor.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add core/focus_monitor.py tests/test_focus_monitor.py
git commit -m "feat: add focus monitor for foreground window detection"
```

---

### Task 2: Focus tracker widget — toggle + cycling app selector

**Files:**
- Create: `ui/focus_tracker.py`
- Create: `tests/test_focus_tracker.py`
- Modify: `ui/icons.py:5` (add FOCUS icon)

- [ ] **Step 1: Add icon constant**

In `ui/icons.py`, add after line 7 (after `START`):

```python
    # Focus tracking toggle
    FOCUS_ON = "ph.eye-bold"
    FOCUS_OFF = "ph.eye-slash-bold"
```

- [ ] **Step 2: Commit icon addition**

```bash
git add ui/icons.py
git commit -m "feat: add focus tracking icons"
```

- [ ] **Step 3: Write failing tests for FocusTracker**

```python
# tests/test_focus_tracker.py
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pytest
from unittest.mock import MagicMock


def make_tracker(saved_apps=None, enabled=False, slot_index=0):
    """Create a FocusTracker with a mock theme, no Qt app needed for logic tests."""
    from ui.focus_tracker import FocusTrackerState
    return FocusTrackerState(
        saved_apps=saved_apps or [None] * 5,
        enabled=enabled,
        slot_index=slot_index,
    )


def test_default_state():
    state = make_tracker()
    assert state.enabled is False
    assert state.slot_index == 0
    assert state.saved_apps == [None, None, None, None, None]
    assert state.current_app is None


def test_toggle_enabled():
    state = make_tracker()
    state.enabled = True
    assert state.enabled is True


def test_set_app_in_slot():
    state = make_tracker()
    state.set_app(0, "Photoshop")
    assert state.saved_apps[0] == "Photoshop"
    assert state.current_app == "Photoshop"


def test_clear_slot():
    state = make_tracker(saved_apps=["Photoshop", None, None, None, None])
    state.clear_slot(0)
    assert state.saved_apps[0] is None
    assert state.current_app is None


def test_next_slot_wraps():
    state = make_tracker(slot_index=4)
    state.next_slot()
    assert state.slot_index == 0


def test_prev_slot_wraps():
    state = make_tracker(slot_index=0)
    state.prev_slot()
    assert state.slot_index == 4


def test_cycle_through_all_slots():
    state = make_tracker(
        saved_apps=["Photoshop", "Krita", None, None, "Blender"],
        slot_index=0,
    )
    order = [state.current_app]
    for _ in range(4):
        state.next_slot()
        order.append(state.current_app)
    assert order == ["Photoshop", "Krita", None, None, "Blender"]


def test_save_state():
    state = make_tracker(
        saved_apps=["Photoshop", None, "Krita", None, None],
        enabled=True,
        slot_index=2,
    )
    data = state.save_state()
    assert data == {
        "focus_enabled": True,
        "focus_slot": 2,
        "focus_apps": ["Photoshop", None, "Krita", None, None],
    }


def test_restore_state():
    state = make_tracker()
    state.restore_state({
        "focus_enabled": True,
        "focus_slot": 1,
        "focus_apps": ["PS", "Krita", None, None, None],
    })
    assert state.enabled is True
    assert state.slot_index == 1
    assert state.current_app == "Krita"


def test_restore_state_missing_keys():
    state = make_tracker()
    state.restore_state({})
    assert state.enabled is False
    assert state.slot_index == 0
    assert state.saved_apps == [None] * 5


def test_slot_count_fixed_at_five():
    state = make_tracker()
    assert len(state.saved_apps) == 5


def test_restore_state_truncates_long_list():
    state = make_tracker()
    state.restore_state({
        "focus_apps": ["A", "B", "C", "D", "E", "F", "G"],
    })
    assert len(state.saved_apps) == 5
    assert state.saved_apps == ["A", "B", "C", "D", "E"]


def test_restore_state_pads_short_list():
    state = make_tracker()
    state.restore_state({
        "focus_apps": ["A", "B"],
    })
    assert len(state.saved_apps) == 5
    assert state.saved_apps == ["A", "B", None, None, None]
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `python -m pytest tests/test_focus_tracker.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ui.focus_tracker'`

- [ ] **Step 5: Implement FocusTrackerState (logic only, no Qt)**

```python
# ui/focus_tracker.py
"""Focus-aware pause: toggle + cycling app selector widget."""

NUM_SLOTS = 5


class FocusTrackerState:
    """Pure logic for focus tracker — no Qt dependency, easy to test."""

    def __init__(self, saved_apps=None, enabled=False, slot_index=0):
        self.enabled = enabled
        self.slot_index = slot_index
        if saved_apps is None:
            self.saved_apps = [None] * NUM_SLOTS
        else:
            self.saved_apps = list(saved_apps)

    @property
    def current_app(self):
        return self.saved_apps[self.slot_index]

    def set_app(self, slot, name):
        self.saved_apps[slot] = name

    def clear_slot(self, slot):
        self.saved_apps[slot] = None

    def next_slot(self):
        self.slot_index = (self.slot_index + 1) % NUM_SLOTS

    def prev_slot(self):
        self.slot_index = (self.slot_index - 1) % NUM_SLOTS

    def save_state(self):
        return {
            "focus_enabled": self.enabled,
            "focus_slot": self.slot_index,
            "focus_apps": list(self.saved_apps),
        }

    def restore_state(self, data):
        self.enabled = data.get("focus_enabled", False)
        self.slot_index = data.get("focus_slot", 0)
        apps = data.get("focus_apps", [None] * NUM_SLOTS)
        # Normalize to exactly NUM_SLOTS entries
        apps = list(apps[:NUM_SLOTS])
        while len(apps) < NUM_SLOTS:
            apps.append(None)
        self.saved_apps = apps
        self.slot_index = min(self.slot_index, NUM_SLOTS - 1)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest tests/test_focus_tracker.py -v`
Expected: All 13 tests PASS

- [ ] **Step 7: Commit**

```bash
git add ui/focus_tracker.py tests/test_focus_tracker.py
git commit -m "feat: add FocusTrackerState with save/restore and slot cycling"
```

---

### Task 3: Focus tracker Qt widget — UI component

**Files:**
- Modify: `ui/focus_tracker.py` (add FocusTrackerWidget class)
- Modify: `ui/scales.py` (add font/spacing constants)

- [ ] **Step 1: Add scale constants**

In `ui/scales.py`, add after line 193 (`FONT_LIMIT_SEP = 10`), inside the `S` class:

```python
    # Focus tracker
    FONT_FOCUS_BTN = 9
    FOCUS_DROPDOWN_MAX = 10
```

- [ ] **Step 2: Implement FocusTrackerWidget**

Append to `ui/focus_tracker.py`:

```python
import qtawesome as qta
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QLabel, QPushButton,
                              QMenu, QWidgetAction)
from PyQt6.QtCore import Qt, pyqtSignal
from ui.icons import Icons
from ui.scales import S
from ui.widgets import IconButton
from core.focus_monitor import list_window_apps


class FocusTrackerWidget(QWidget):
    """Toggle + cycling app-selector for focus-aware pause."""

    tracking_changed = pyqtSignal(bool, str)  # (enabled, app_name_or_empty)

    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._state = FocusTrackerState()

        self._build()

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(0, 0, 0, 0)

        # Toggle button (icon style)
        self._toggle_btn = IconButton(size=S.ICON_HEADER)
        self._toggle_btn.setToolTip("Focus-aware pause")
        self._toggle_btn.clicked.connect(self._on_toggle)
        layout.addWidget(self._toggle_btn)

        # Label
        self._label = QLabel("Pause with app")
        self._label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._label)

        # App selector button (cycles on click)
        self._app_btn = QPushButton("Select")
        self._app_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._app_btn.setToolTip("Left-click: next app | Right-click: prev app")
        self._app_btn.clicked.connect(self._on_next)
        self._app_btn.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu)
        self._app_btn.customContextMenuRequested.connect(self._on_prev)
        self._app_btn.hide()
        layout.addWidget(self._app_btn)

        # Action button: arrow (open list) or x (clear slot)
        self._action_btn = IconButton(size=S.ICON_HEADER)
        self._action_btn.clicked.connect(self._on_action)
        self._action_btn.hide()
        layout.addWidget(self._action_btn)

        layout.addStretch()
        self._update_display()

    def _on_toggle(self):
        self._state.enabled = not self._state.enabled
        self._update_display()
        self._emit()

    def _on_next(self):
        self._state.next_slot()
        self._update_display()
        self._emit()

    def _on_prev(self, pos=None):
        self._state.prev_slot()
        self._update_display()
        self._emit()

    def _on_action(self):
        if self._state.current_app:
            # Clear current slot
            self._state.clear_slot(self._state.slot_index)
            self._update_display()
            self._emit()
        else:
            # Show running apps dropdown
            self._show_app_list()

    def _show_app_list(self):
        apps = list_window_apps()
        if not apps:
            return
        menu = QMenu(self)
        t = self.theme
        menu.setStyleSheet(
            f"QMenu {{ background: {t.bg}; color: {t.text_primary}; "
            f"border: 1px solid {t.border}; font-family: 'Lexend'; "
            f"font-size: {S.FONT_FOCUS_BTN}px; "
            f"max-height: {S.FOCUS_DROPDOWN_MAX * 24}px; }}"
            f"QMenu::item {{ padding: 4px 12px; }}"
            f"QMenu::item:selected {{ background: {t.bg_active}; }}")
        for app_name in apps:
            action = menu.addAction(app_name)
            action.triggered.connect(
                lambda checked, n=app_name: self._pick_app(n))
        menu.exec(self._action_btn.mapToGlobal(
            self._action_btn.rect().bottomLeft()))

    def _pick_app(self, name):
        self._state.set_app(self._state.slot_index, name)
        self._update_display()
        self._emit()

    def _update_display(self):
        t = self.theme
        enabled = self._state.enabled

        # Toggle icon
        icon_name = Icons.FOCUS_ON if enabled else Icons.FOCUS_OFF
        icon_color = t.text_secondary if enabled else t.text_hint
        self._toggle_btn.setIcon(qta.icon(icon_name, color=icon_color))

        if not enabled:
            self._label.setText("Pause with app")
            self._label.setStyleSheet(
                f"color: {t.text_hint}; font-size: {S.FONT_FOCUS_BTN}px; "
                f"font-family: 'Lexend'; font-weight: 400;")
            self._app_btn.hide()
            self._action_btn.hide()
            return

        # Enabled — show app selector
        self._label.setText("Pause with:")
        self._label.setStyleSheet(
            f"color: {t.text_hint}; font-size: {S.FONT_FOCUS_BTN}px; "
            f"font-family: 'Lexend'; font-weight: 400;")

        current = self._state.current_app
        if current:
            self._app_btn.setText(current)
            self._app_btn.setStyleSheet(
                f"color: {t.accent}; font-size: {S.FONT_FOCUS_BTN}px; "
                f"font-weight: 500; font-family: 'Lexend'; "
                f"background: transparent; border: none; padding: 0; "
                f"text-decoration: underline;")
            # Show X to clear
            self._action_btn.setIcon(
                qta.icon(Icons.CLOSE, color=t.text_hint))
            self._action_btn.setToolTip("Clear this slot")
        else:
            self._app_btn.setText("Select")
            self._app_btn.setStyleSheet(
                f"color: {t.text_hint}; font-size: {S.FONT_FOCUS_BTN}px; "
                f"font-weight: 400; font-family: 'Lexend'; "
                f"background: transparent; border: none; padding: 0;")
            # Show arrow to pick
            self._action_btn.setIcon(
                qta.icon("ph.caret-down-bold", color=t.text_hint))
            self._action_btn.setToolTip("Choose app to track")

        self._app_btn.show()
        self._action_btn.show()

    def _emit(self):
        app = self._state.current_app or ""
        self.tracking_changed.emit(self._state.enabled, app)

    # ---- Public API for save/restore ----

    def save_state(self):
        return self._state.save_state()

    def restore_state(self, data):
        self._state.restore_state(data)
        self._update_display()

    def apply_theme(self):
        self._update_display()

    @property
    def is_tracking(self):
        """True if enabled and an app is selected."""
        return self._state.enabled and self._state.current_app is not None

    @property
    def tracked_app(self):
        """Name of the app being tracked, or None."""
        return self._state.current_app if self._state.enabled else None
```

- [ ] **Step 3: Run all tests**

Run: `python -m pytest tests/ -v`
Expected: All tests PASS (focus_tracker tests still pass, no regressions)

- [ ] **Step 4: Commit**

```bash
git add ui/focus_tracker.py ui/scales.py
git commit -m "feat: add FocusTrackerWidget with dropdown and cycling"
```

---

### Task 4: Integrate FocusTracker into BottomBar — replace groups label

**Files:**
- Modify: `ui/bottom_bar.py`

- [ ] **Step 1: Add FocusTrackerWidget to BottomBar**

In `ui/bottom_bar.py`, add import at top:

```python
from ui.focus_tracker import FocusTrackerWidget
```

In `_build()`, replace the `_groups_label` creation (lines 39-42) with:

```python
        self._focus_tracker = FocusTrackerWidget(self.theme, parent=self)
        summary_col.addWidget(self._focus_tracker)
```

Remove `self._groups_label` entirely — it is no longer created or referenced.

- [ ] **Step 2: Remove groups label references from summary methods**

Replace `update_summary_quick` method:

```python
    def update_summary_quick(self, image_count, timer_seconds):
        if image_count == 0:
            self._total_label.setText("")
            self._limit_sep.hide()
            self._limit_btn.hide()
        else:
            total = image_count * timer_seconds
            self._total_label.setText(format_time(total))
            self._limit_sep.show()
            self._limit_btn.show()
            self._update_limit_display()
```

Replace `update_summary_class` method:

```python
    def update_summary_class(self, image_count, class_groups):
        if image_count == 0:
            self._total_label.setText("")
            self._limit_sep.hide()
            self._limit_btn.hide()
        elif class_groups:
            dur = total_duration(class_groups)
            self._total_label.setText(format_time(dur))
            self._limit_sep.show()
            self._limit_btn.show()
            self._update_limit_display()
        else:
            self._total_label.setText("")
            self._limit_sep.hide()
            self._limit_btn.hide()
```

- [ ] **Step 3: Update apply_theme to style focus tracker**

In `apply_theme()`, remove the `_groups_label` styling (lines 169-171) and add:

```python
        self._focus_tracker.theme = t
        self._focus_tracker.apply_theme()
```

- [ ] **Step 4: Update save_state/restore_state**

Replace `save_state`:

```python
    def save_state(self):
        state = {
            "session_limit": self.get_session_limit(),
        }
        state.update(self._focus_tracker.save_state())
        return state
```

Replace `restore_state`:

```python
    def restore_state(self, data):
        session_limit = data.get("session_limit")
        if session_limit is not None:
            for i, (s, _) in enumerate(SESSION_LIMIT_PRESETS):
                if s == session_limit:
                    self._session_limit_index = i
                    break
        self._session_limit_index = min(self._session_limit_index,
                                        len(SESSION_LIMIT_PRESETS) - 1)
        self._focus_tracker.restore_state(data)
```

- [ ] **Step 5: Reorder layout — total+limit first, focus tracker below**

In `_build()`, reorder `summary_col` children so total/limit comes first, focus tracker below:

```python
        # Summary info (left side)
        summary_widget = QWidget()
        summary_col = QVBoxLayout(summary_widget)
        summary_col.setSpacing(0)
        summary_col.setContentsMargins(0, 0, 0, 0)

        summary_time = QHBoxLayout()
        summary_time.setSpacing(S.SUMMARY_TIME_SPACING)
        summary_time.setContentsMargins(0, 0, 0, 0)

        self._total_label = QLabel("")
        self._total_label.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self._limit_sep = QLabel("\u00b7")
        self._limit_sep.hide()

        self._limit_btn = QPushButton("no limit")
        self._limit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._limit_btn.setToolTip("Session time limit")
        self._limit_btn.clicked.connect(self._next_limit)
        self._limit_btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._limit_btn.customContextMenuRequested.connect(self._prev_limit)
        self._limit_btn.hide()

        summary_time.addWidget(self._total_label)
        summary_time.addWidget(self._limit_sep)
        summary_time.addWidget(self._limit_btn)
        summary_time.addStretch()

        summary_col.addLayout(summary_time)

        # Focus tracker (below total+limit)
        self._focus_tracker = FocusTrackerWidget(self.theme, parent=self)
        summary_col.addWidget(self._focus_tracker)
```

- [ ] **Step 6: Run all tests**

Run: `python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add ui/bottom_bar.py
git commit -m "feat: replace groups label with focus tracker in bottom bar"
```

---

### Task 5: Wire focus monitoring into ViewerWindow — auto-pause on focus loss

**Files:**
- Modify: `ui/viewer_window.py`

- [ ] **Step 1: Add focus polling timer to ViewerWindow.__init__**

In `ui/viewer_window.py`, add import at top:

```python
from core.focus_monitor import get_foreground_app
```

In `__init__`, after `self._session_elapsed = 0` (line 146), add:

```python
        self._focus_app = settings.get("focus_app")  # app name or None
        self._focus_enabled = settings.get("focus_enabled", False)
        self._auto_paused = False
```

After the main `_qtimer` setup (line 290), add the focus polling timer:

```python
        # Focus polling timer (checks foreground window every 500ms)
        self._focus_timer = QTimer(self)
        self._focus_timer.setInterval(500)
        self._focus_timer.timeout.connect(self._check_focus)
        if self._focus_enabled and self._focus_app:
            self._focus_timer.start()
```

- [ ] **Step 2: Implement _check_focus method**

Add after `_toggle_pause` method (after line 481):

```python
    def _check_focus(self):
        """Poll foreground window — auto-pause if tracked app lost focus."""
        if not self._focus_enabled or not self._focus_app:
            return
        fg = get_foreground_app()
        if fg is None:
            return
        app_lost_focus = fg.lower() != self._focus_app.lower()
        if app_lost_focus and not self._paused:
            self._auto_paused = True
            self._toggle_pause()
```

- [ ] **Step 3: Prevent auto-resume — only track auto_paused flag**

Modify `_toggle_pause` to clear `_auto_paused` when user manually resumes:

```python
    def _toggle_pause(self):
        self._paused = not self._paused
        if self._paused:
            self._qtimer.stop()
        else:
            self._auto_paused = False
            self._qtimer.start()
        self._update_center_icon()
        self._update_coffee()
```

- [ ] **Step 4: Stop focus timer on close/finish**

In `_finish` method, add before `self._qtimer.stop()`:

```python
        self._focus_timer.stop()
```

In `closeEvent`, add before `self._qtimer.stop()`:

```python
        self._focus_timer.stop()
```

- [ ] **Step 5: Pass focus settings from SettingsWindow to ViewerWindow**

In `ui/settings_window.py`, in `_start_slideshow` method, update the `settings` dict (line 621-626):

```python
        focus_state = self._bottom_bar._focus_tracker
        settings = {
            "order": "sequential",
            "topmost": self._topmost,
            "viewer_size": getattr(self, "_last_viewer_size", None),
            "session_limit": self._bottom_bar.get_session_limit(),
            "focus_enabled": focus_state.is_tracking,
            "focus_app": focus_state.tracked_app,
        }
```

- [ ] **Step 6: Run all tests**

Run: `python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add ui/viewer_window.py ui/settings_window.py
git commit -m "feat: wire focus monitoring into viewer — auto-pause on app focus loss"
```

---

### Task 6: Session persistence — save and restore focus tracker state

**Files:**
- Modify: `ui/settings_window.py`

- [ ] **Step 1: Verify save_state already includes focus data**

The BottomBar `save_state` (modified in Task 4) already merges `_focus_tracker.save_state()`. The SettingsWindow `_save_session` (line 689) calls `self._bottom_bar.save_state()` and spreads it into the data dict. The `_restore_session` (line 664) passes data to `self._bottom_bar.restore_state(data)`, which now calls `self._focus_tracker.restore_state(data)`.

No code changes needed — verify with a manual test:
1. Enable focus tracking, pick an app
2. Close Drawer
3. Reopen — focus toggle should be on, app should be remembered

- [ ] **Step 2: Write a test for round-trip persistence**

```python
# Add to tests/test_session.py

def test_focus_state_round_trip():
    """Focus tracker state survives save/load cycle."""
    data = {
        "focus_enabled": True,
        "focus_slot": 2,
        "focus_apps": ["Photoshop", None, "Krita", None, None],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        path = f.name
    save_session(data, path)
    loaded = load_session(path)
    assert loaded["focus_enabled"] is True
    assert loaded["focus_slot"] == 2
    assert loaded["focus_apps"] == ["Photoshop", None, "Krita", None, None]
    os.unlink(path)
```

- [ ] **Step 3: Run all tests**

Run: `python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add tests/test_session.py
git commit -m "test: add focus state persistence round-trip test"
```

---

### Task 7: Manual testing and polish

**Files:**
- Possibly: `ui/focus_tracker.py`, `ui/bottom_bar.py` (minor adjustments)

- [ ] **Step 1: Verify full flow manually**

Launch the app with `python main.py` and test:
1. Toggle focus tracking on/off — label and selector appear/disappear
2. Click arrow on empty slot — dropdown shows running apps
3. Select an app — slot fills, arrow becomes X
4. Left-click cycles slots, right-click cycles backward
5. Start a session — timer auto-pauses when tracked app loses focus
6. Manual resume works (spacebar or click)
7. Close and reopen — state persists

- [ ] **Step 2: Fix any visual/layout issues found**

Adjust spacing, alignment, or font sizes as needed based on manual testing.

- [ ] **Step 3: Run full test suite**

Run: `python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 4: Commit any polish**

```bash
git add -u
git commit -m "fix: polish focus tracker layout and styling"
```
