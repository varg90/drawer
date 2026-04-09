# Session Limit Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the duration picker stepper with an inline clickable session limit in the summary, and make session limit a standalone viewer countdown independent of tier distribution.

**Architecture:** Tiers distribute ALL images (no time budget constraint). Session limit is an optional viewer-side countdown that ends the slideshow when elapsed time is reached. The limit control lives inline in the summary row as a clickable label.

**Tech Stack:** Python, PyQt6, pytest

---

### Task 1: Update constants — replace SESSION_PRESETS with SESSION_LIMIT_PRESETS

**Files:**
- Modify: `core/constants.py:17-27`
- Modify: `tests/test_class_mode.py` (no changes needed — doesn't import SESSION_PRESETS)

- [ ] **Step 1: Replace SESSION_PRESETS in constants.py**

Replace the `SESSION_PRESETS` list with `SESSION_LIMIT_PRESETS` that includes a `None` "off" option:

```python
SESSION_LIMIT_PRESETS = [
    (None, "no limit"),
    (300, "5m"),
    (600, "10m"),
    (900, "15m"),
    (1800, "30m"),
    (2700, "45m"),
    (3600, "1h"),
    (5400, "1.5h"),
    (7200, "2h"),
    (10800, "3h"),
]
```

Delete `SESSION_PRESETS`.

- [ ] **Step 2: Run tests to check for breakage**

Run: `python -m pytest tests/ -q`
Expected: Some failures in settings_window-related tests (if any import SESSION_PRESETS). Fix imports in later tasks.

- [ ] **Step 3: Commit**

```bash
git add core/constants.py
git commit -m "refactor: replace SESSION_PRESETS with SESSION_LIMIT_PRESETS"
```

---

### Task 2: Remove duration picker scales

**Files:**
- Modify: `ui/scales.py:31,39,41-43`
- Modify: `tests/test_scales.py:26`

- [ ] **Step 1: Remove duration picker constants from scales.py**

Delete these lines from `class S`:
```python
    FONT_DURATION = 18
    SPACING_DURATION = 12
    DURATION_ARROW = 14
    DURATION_ARROW_BTN = 22
```

- [ ] **Step 2: Update test_scales.py**

In `test_font_sizes`, remove the `FONT_DURATION` assertion:

```python
def test_font_sizes():
    assert S.FONT_TITLE == 11
    assert S.FONT_BUTTON == 10
    assert S.FONT_LABEL == 9
```

- [ ] **Step 3: Run tests**

Run: `python -m pytest tests/test_scales.py -v`
Expected: All pass.

- [ ] **Step 4: Commit**

```bash
git add ui/scales.py tests/test_scales.py
git commit -m "refactor: remove duration picker scales"
```

---

### Task 3: Rework auto_distribute to cover all images (no time budget)

**Files:**
- Modify: `core/class_mode.py:7-73`
- Modify: `tests/test_class_mode.py`

- [ ] **Step 1: Write failing test — all images must be distributed**

Add to `tests/test_class_mode.py`:

```python
def test_auto_distribute_all_images_covered():
    """Every image gets a timer — no overflow."""
    tiers = [(30, "30s"), (60, "1m")]
    groups = auto_distribute(20, custom_tiers=tiers)
    assert sum(c for c, _ in groups) == 20


def test_auto_distribute_no_time_budget():
    """Without time budget, distribute all images across tiers."""
    groups = auto_distribute(10, custom_tiers=[(60, "1m"), (300, "5m")])
    assert sum(c for c, _ in groups) == 10
    used_timers = set(t for _, t in groups)
    assert used_timers == {60, 300}


def test_auto_distribute_single_tier_all_images():
    tiers = [(300, "5m")]
    groups = auto_distribute(8, custom_tiers=tiers)
    assert groups == [(8, 300)]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_class_mode.py::test_auto_distribute_all_images_covered -v`
Expected: FAIL (signature mismatch — `total_seconds` is required)

- [ ] **Step 3: Rework auto_distribute**

Change `auto_distribute` to no longer require `total_seconds`. It distributes ALL images across selected tiers evenly (round-robin from cheapest to most expensive):

```python
def auto_distribute(num_images, custom_tiers=None):
    """
    Distribute num_images across tiers evenly, short-to-long.
    All images are assigned — no overflow.

    custom_tiers: list of (seconds, label). Uses medium template if None.
    Returns list of (count, timer_seconds) tuples.
    """
    if num_images <= 0:
        return []

    if custom_tiers and len(custom_tiers) > 0:
        tiers = sorted(custom_tiers, key=lambda t: t[0])
    else:
        tiers = CLASS_MODE_TEMPLATES["medium"]

    num_tiers = len(tiers)
    # Start with 1 image per tier (up to num_images)
    usable_tiers = tiers[:num_images]
    num_tiers = len(usable_tiers)
    groups = [(1, t) for t, _ in usable_tiers]
    remaining = num_images - num_tiers

    # Round-robin remaining images across tiers
    while remaining > 0:
        for i in range(num_tiers):
            if remaining <= 0:
                break
            old_count, t = groups[i]
            groups[i] = (old_count + 1, t)
            remaining -= 1

    return groups
```

- [ ] **Step 4: Update existing tests**

The old tests pass `total_seconds` as second argument. Update them to use the new signature (no `total_seconds`):

```python
def test_auto_distribute_basic():
    groups = auto_distribute(10, custom_tiers=[(30, "30s"), (60, "1m"), (300, "5m")])
    assert len(groups) > 0
    assert sum(c for c, _ in groups) == 10


def test_auto_distribute_single_image():
    groups = auto_distribute(1, custom_tiers=[(60, "1m"), (300, "5m")])
    assert sum(c for c, _ in groups) == 1


def test_auto_distribute_zero():
    assert auto_distribute(0) == []


def test_auto_distribute_increasing_timers():
    groups = auto_distribute(12, custom_tiers=[(30, "30s"), (60, "1m"), (300, "5m")])
    timers = [t for _, t in groups]
    assert timers == sorted(timers)


def test_auto_distribute_custom_tiers():
    tiers = [(60, "1m"), (300, "5m")]
    groups = auto_distribute(10, custom_tiers=tiers)
    for _, t in groups:
        assert t in (60, 300)


def test_auto_distribute_custom_single_tier():
    tiers = [(300, "5m")]
    groups = auto_distribute(5, custom_tiers=tiers)
    assert all(t == 300 for _, t in groups)


def test_auto_distribute_uses_all_tiers():
    tiers = [(60, "1m"), (300, "5m"), (600, "10m")]
    groups = auto_distribute(10, custom_tiers=tiers)
    used_timers = set(t for _, t in groups)
    assert used_timers == {60, 300, 600}
```

Remove these tests (no longer applicable — no time budget):
- `test_auto_distribute_fits_time`
- `test_auto_distribute_long_session`
- `test_auto_distribute_very_long`
- `test_auto_distribute_plenty_of_time`

- [ ] **Step 5: Run all tests**

Run: `python -m pytest tests/test_class_mode.py -v`
Expected: All pass.

- [ ] **Step 6: Commit**

```bash
git add core/class_mode.py tests/test_class_mode.py
git commit -m "refactor: auto_distribute covers all images, no time budget"
```

---

### Task 4: Rework settings_window — remove stepper, add inline limit

**Files:**
- Modify: `ui/settings_window.py`

This is the largest task. It removes the stepper UI, adds the clickable limit label, and rewires `_auto_distribute` to use the new signature.

- [ ] **Step 1: Update imports**

Replace `SESSION_PRESETS` with `SESSION_LIMIT_PRESETS` in the import line:

```python
from core.constants import (SUPPORTED_FORMATS, TIMER_PRESETS, SESSION_LIMIT_PRESETS,
                            ALL_TIERS)
```

- [ ] **Step 2: Update __init__ state**

Replace:
```python
self._session_index = 5  # default 1h
```
With:
```python
self._session_limit_index = 0  # default: no limit (None)
```

Remove `self._manual_groups` (no longer needed — no time budget).

- [ ] **Step 3: Remove stepper UI from _build_ui**

Delete the entire duration picker section (section 3):
```python
        # ── 3. Duration picker ─────────────────────────────────────────────
        dur_row = QHBoxLayout()
        ...
        root.addLayout(dur_row)
        root.addSpacing(S.SPACING_DURATION)
```

- [ ] **Step 4: Replace _total_label with clickable limit row**

Replace the summary section (section 5) with:

```python
        # ── 5. Summary line (groups + total + limit) ──────────────────────
        self._groups_label = QLabel("")
        self._groups_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        root.addWidget(self._groups_label)

        summary_row = QHBoxLayout()
        summary_row.setSpacing(4)
        summary_row.setContentsMargins(0, 2, 0, 0)

        self._total_label = QLabel("")
        self._total_label.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self._limit_sep = QLabel("\u00b7")

        self._limit_btn = QPushButton("no limit")
        self._limit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._limit_btn.setToolTip("Session time limit")
        self._limit_btn.clicked.connect(self._next_limit)
        self._limit_btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._limit_btn.customContextMenuRequested.connect(self._prev_limit)

        summary_row.addWidget(self._total_label)
        summary_row.addWidget(self._limit_sep)
        summary_row.addWidget(self._limit_btn)
        summary_row.addStretch()
        root.addLayout(summary_row)
```

- [ ] **Step 5: Add limit cycling methods**

Replace `_prev_session`, `_next_session`, `_update_session_display`, `_get_session_seconds` with:

```python
    def _next_limit(self):
        self._session_limit_index = (self._session_limit_index + 1) % len(SESSION_LIMIT_PRESETS)
        self._update_limit_display()

    def _prev_limit(self, pos=None):
        self._session_limit_index = (self._session_limit_index - 1) % len(SESSION_LIMIT_PRESETS)
        self._update_limit_display()

    def _get_session_limit(self):
        return SESSION_LIMIT_PRESETS[self._session_limit_index][0]

    def _update_limit_display(self):
        secs, label = SESSION_LIMIT_PRESETS[self._session_limit_index]
        t = self.theme
        if secs is None:
            self._limit_btn.setText("no limit")
            self._limit_btn.setStyleSheet(
                f"color: {t.text_hint}; font-size: 9px; font-weight: 500; "
                f"background: transparent; border: none; padding: 0;")
        else:
            self._limit_btn.setText(f"limit: {label}")
            self._limit_btn.setStyleSheet(
                f"color: {t.accent}; font-size: 9px; font-weight: 500; "
                f"background: transparent; border: none; padding: 0; "
                f"text-decoration: underline;")
```

- [ ] **Step 6: Simplify _auto_distribute**

Remove the time-budget logic. New version:

```python
    def _auto_distribute(self):
        if not self.images:
            return
        num_images = len(self.images)
        auto_groups = auto_distribute(num_images, custom_tiers=self._get_selected_tiers())
        self._class_groups = auto_groups
        self._apply_class_timers()
        self._update_groups_display()
        self._update_summary()
```

- [ ] **Step 7: Update _update_groups_display**

Show total duration on the `_total_label`, limit on `_limit_btn`:

```python
    def _update_groups_display(self):
        if not self._class_groups:
            self._groups_label.setText("")
            self._total_label.setText("")
            self._limit_sep.hide()
            self._limit_btn.hide()
            return
        parts = []
        for count, timer in self._class_groups:
            if timer >= 3600:
                t = f"{timer // 3600}h"
            elif timer >= 60:
                t = f"{timer // 60}m"
            else:
                t = f"{timer}s"
            parts.append(f"{count}x{t}")
        self._groups_label.setText("  ".join(parts))
        dur = total_duration(self._class_groups)
        self._total_label.setText(format_time(dur))
        self._limit_sep.show()
        self._limit_btn.show()
        self._update_limit_display()
```

- [ ] **Step 8: Update _apply_theme for limit controls**

In `_apply_theme`, remove the duration picker styling block (the `_dur_active`, `_dur_color`, `_dur_text`, `self._ses_left`, `self._ses_right`, `self._ses_display` lines). Add:

```python
        # Summary
        self._groups_label.setStyleSheet(
            f"color: {t.text_secondary}; font-size: {S.FONT_HINT}px; font-weight: 500;")
        self._total_label.setStyleSheet(
            f"color: {t.text_secondary}; font-size: {S.FONT_TOTAL}px; font-weight: 500;")
        self._limit_sep.setStyleSheet(f"color: {t.text_hint}; font-size: 10px;")
        self._update_limit_display()
```

- [ ] **Step 9: Update _set_timer_mode**

In class mode, hide/show the limit controls:

```python
    def _set_timer_mode(self, mode):
        self._timer_mode = mode
        if mode == "quick":
            for btn, _ in self._quick_btns:
                btn.show()
            for btn, _ in self._class_btns:
                btn.hide()
            timer = self.get_timer_seconds()
            for img in self.images:
                img.timer = timer
            self._limit_sep.hide()
            self._limit_btn.hide()
        else:
            for btn, _ in self._quick_btns:
                btn.hide()
            for btn, _ in self._class_btns:
                btn.show()
            self._limit_sep.show()
            self._limit_btn.show()
        self._update_mode_buttons()
        self._update_summary()
        self._apply_theme()
        if self._editor_visible:
            self.editor.refresh(self.images)
```

- [ ] **Step 10: Update _start_slideshow**

Pass `session_limit` to the viewer:

```python
        settings = {
            "order": "sequential",
            "topmost": self._topmost,
            "viewer_size": getattr(self, "_last_viewer_size", None),
            "session_limit": self._get_session_limit(),
        }
```

- [ ] **Step 11: Update session save/restore**

In `_save_session`, replace `session_seconds` with `session_limit`:

```python
            "session_limit": self._get_session_limit(),
```

In `_restore_session`, replace session index restoration:

```python
        session_limit = data.get("session_limit")
        if session_limit is not None:
            for i, (s, _) in enumerate(SESSION_LIMIT_PRESETS):
                if s == session_limit:
                    self._session_limit_index = i
                    break
        else:
            self._session_limit_index = 0
```

Remove the old `session_seconds` restoration block.

- [ ] **Step 12: Run tests**

Run: `python -m pytest tests/ -q`
Expected: All pass (no direct tests for settings_window UI).

- [ ] **Step 13: Commit**

```bash
git add ui/settings_window.py
git commit -m "feat: replace duration stepper with inline session limit"
```

---

### Task 5: Add session limit countdown to viewer

**Files:**
- Modify: `ui/viewer_window.py`

- [ ] **Step 1: Add session tracking state in __init__**

After `self._is_warning = False` (line 102), add:

```python
        self._session_limit = settings.get("session_limit")  # seconds or None
        self._session_elapsed = 0
```

- [ ] **Step 2: Add session label to bottom area**

After the coffee label creation (line 189), add a session remaining label:

```python
        # Session limit label
        self._session_label = QLabel(self)
        self._session_label.setStyleSheet(
            "color: rgba(255,255,255,75); font-size: 12px; background: transparent;")
        self._session_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._session_label.hide()
```

Add `self._session_label` to `self._hover_widgets` list (before the progress bar):

```python
        self._hover_widgets = [
            self._top_left, self._top_right, self._center_btn,
            self._left_nav, self._right_nav,
            self._timer_label, self._counter_label,
            self._session_label, self._progress_bar,
        ]
```

- [ ] **Step 3: Update _tick to track session elapsed**

In `_tick`, after `self._countdown -= 1`, add session elapsed tracking:

```python
    def _tick(self):
        if self._paused:
            return
        self._countdown -= 1
        self._session_elapsed += 1
        self._update_timer_display()
        self._update_session_display()
        if self._session_limit and self._session_elapsed >= self._session_limit:
            self._finish()
            return
        if self._countdown <= 0:
            self._advance()
```

- [ ] **Step 4: Add _update_session_display method**

After `_update_timer_display`, add:

```python
    def _update_session_display(self):
        if not self._session_limit:
            self._session_label.hide()
            return
        remaining = self._session_limit - self._session_elapsed
        if remaining < 0:
            remaining = 0
        self._session_label.setText(format_time(remaining))
        self._session_label.show()
        # Warning color when < 5 minutes remaining
        if remaining <= 300:
            self._session_label.setStyleSheet(
                "color: rgba(255,85,85,160); font-size: 12px; background: transparent;")
        else:
            self._session_label.setStyleSheet(
                "color: rgba(255,255,255,75); font-size: 12px; background: transparent;")
```

- [ ] **Step 5: Update _layout_bottom to position session label**

Update `_layout_bottom` to place the session label between the coffee/timer and counter:

```python
    def _layout_bottom(self, w, h):
        lbl_h = 24
        bottom_y = h - lbl_h - 8
        x = 10
        if self._coffee_label.isVisible():
            self._coffee_label.setFixedSize(20, 20)
            self._coffee_label.move(x, bottom_y + 2)
            x += 26
        self._timer_label.setGeometry(x, bottom_y, 80, lbl_h)
        # Session remaining — right of timer
        if self._session_limit:
            self._session_label.setGeometry(x + 80, bottom_y + 4, 60, lbl_h)
        self._counter_label.setGeometry(w - 70, bottom_y, 60, lbl_h)
        self._counter_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
```

- [ ] **Step 6: Call _update_session_display on first image show**

In `_show_current_image`, after `self._schedule_next(img.timer)`, add:

```python
        self._update_session_display()
```

- [ ] **Step 7: Run tests**

Run: `python -m pytest tests/ -q`
Expected: All pass.

- [ ] **Step 8: Manual test**

Run: `python main.py`
Test: Set class mode with tiers, set limit to 5m, start slideshow. Verify session countdown appears and slideshow ends when limit reached.

- [ ] **Step 9: Commit**

```bash
git add ui/viewer_window.py
git commit -m "feat: add session limit countdown to viewer"
```

---

### Task 6: Clean up dead code and final verification

**Files:**
- Modify: `ui/settings_window.py` (remove any leftover references)
- Modify: `core/constants.py` (verify SESSION_PRESETS removed)

- [ ] **Step 1: Grep for dead references**

Search for: `SESSION_PRESETS`, `_ses_left`, `_ses_right`, `_ses_display`, `_session_index`, `FONT_DURATION`, `SPACING_DURATION`, `DURATION_ARROW`, `_manual_groups`, `_prev_session`, `_next_session`.

Remove any remaining references.

- [ ] **Step 2: Run full test suite**

Run: `python -m pytest tests/ -v`
Expected: All pass.

- [ ] **Step 3: Manual smoke test**

Run: `python main.py`
- Quick mode: verify timer buttons work, no limit controls visible
- Class mode: verify tiers distribute all images, limit label clickable, cycles forward/back
- Slideshow: verify session limit ends slideshow, session remaining shown in viewer
- Session restore: close and reopen, verify limit persists

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: clean up dead code from session limit redesign"
```
