# Drop Pin in Class Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make pinning a quick-mode-only feature. Remove pin UI and pin-logic from class mode entirely. In quick mode, pinned images get the current quick-mode timer (no more "own timer" lock). Remove the now-useless "Move to group" context menu everywhere.

**Architecture:** Five focused changes across `core/play_order.py`, `ui/settings_window.py`, and `ui/editor_panel.py`. The core function change is test-driven; UI changes rely on manual smoke testing. All changes compose cleanly — class mode becomes positional-only with no pin special-casing, quick mode keeps pin as play-order priority but drops the timer-lock.

**Tech Stack:** Python 3.14, PyQt6, pytest. The core play-order change is pure Python (no Qt).

**Spec:** `docs/superpowers/specs/2026-04-18-drop-pin-in-class-mode-design.md`

---

## File Structure

- **Modify:** `core/play_order.py` — class-mode branch simplifies to sorted-by-timer (pin ignored).
- **Modify:** `tests/test_play_order.py` — update 2 class-mode tests that assert pin-first-in-tier; add 1 regression test.
- **Modify:** `ui/settings_window.py` — remove 3 pin-skip guards in timer-assignment loops; make `_on_shuffle_clicked` mode-aware (class shuffles all images, quick preserves pinned positions).
- **Modify:** `ui/editor_panel.py` — add `timer_mode` awareness; make `_sort_group_items` mode-aware; remove "Move to group" submenu and its handler branch; suppress context menu in class mode.

---

### Task 1: `build_play_order` — class mode ignores pin

**Files:**
- Modify: `core/play_order.py`
- Test: `tests/test_play_order.py`

- [ ] **Step 1: Update class-mode tests that currently assert pin-first ordering**

In `tests/test_play_order.py`, the following three tests assume class mode sorts pinned-first within each tier. Rewrite their expected outputs to the new "list-order within tier, pin ignored" behavior.

Replace the existing `test_class_multiple_pinned_across_different_tiers`:
```python
def test_class_multiple_pinned_across_different_tiers():
    """Class mode ignores pin flag. Images play in list order within each tier."""
    images = [
        _img("s1.jpg", timer=30),
        _img("P30.jpg", timer=30, pinned=True),
        _img("m1.jpg", timer=300),
        _img("P5m.jpg", timer=300, pinned=True),
        _img("s2.jpg", timer=30),
    ]
    result = build_play_order(images, mode="class")
    paths = [i.path for i in result]
    # 30s tier: s1, P30, s2 (list order, pin ignored).
    # 5m tier: m1, P5m (list order, pin ignored).
    assert paths == ["s1.jpg", "P30.jpg", "s2.jpg", "m1.jpg", "P5m.jpg"]
```

Replace the existing `test_class_multiple_pinned_same_tier_preserve_order`:
```python
def test_class_multiple_pinned_same_tier_preserve_order():
    """Class mode ignores pin flag. Same-tier images play in list order."""
    images = [
        _img("a.jpg", timer=300),
        _img("P1.jpg", timer=300, pinned=True),
        _img("b.jpg", timer=300),
        _img("P2.jpg", timer=300, pinned=True),
    ]
    result = build_play_order(images, mode="class")
    assert [i.path for i in result] == ["a.jpg", "P1.jpg", "b.jpg", "P2.jpg"]
```

The existing `test_class_pinned_first_within_tier` happens to pass under the new behavior too (the pinned image is already at the head of its tier by list order in that test), but rename it and update its docstring to reflect the new semantics:

```python
def test_class_pin_flag_does_not_reorder_tier():
    """Pin flag has no ordering effect in class mode — list order is preserved within tier."""
    images = [
        _img("s1.jpg", timer=30),
        _img("s2.jpg", timer=30),
        _img("m1.jpg", timer=300),
        _img("P15.jpg", timer=900, pinned=True),
        _img("m2.jpg", timer=300),
        _img("l1.jpg", timer=900),
    ]
    result = build_play_order(images, mode="class")
    paths = [i.path for i in result]
    # Tier-ascending, list-order within each tier. Pin is ignored.
    assert paths == ["s1.jpg", "s2.jpg", "m1.jpg", "m2.jpg", "P15.jpg", "l1.jpg"]
```

Add a new regression test at the bottom of the file:
```python
def test_class_mode_ignores_pin_flag():
    """Class mode output is invariant under pin flag changes."""
    images_with_pins = [
        _img("a.jpg", timer=30, pinned=True),
        _img("b.jpg", timer=30),
        _img("c.jpg", timer=300),
        _img("d.jpg", timer=300, pinned=True),
    ]
    images_without_pins = [
        _img("a.jpg", timer=30),
        _img("b.jpg", timer=30),
        _img("c.jpg", timer=300),
        _img("d.jpg", timer=300),
    ]
    pinned_result = [i.path for i in build_play_order(images_with_pins, mode="class")]
    plain_result = [i.path for i in build_play_order(images_without_pins, mode="class")]
    assert pinned_result == plain_result
```

- [ ] **Step 2: Run tests to verify the new expectations fail on current code**

Run: `python -m pytest tests/test_play_order.py -v`
Expected: `test_class_multiple_pinned_across_different_tiers`, `test_class_multiple_pinned_same_tier_preserve_order`, and `test_class_mode_ignores_pin_flag` all FAIL (current class-mode implementation does pinned-first ordering). `test_class_pin_flag_does_not_reorder_tier` passes by coincidence (list order already matches).

- [ ] **Step 3: Simplify the class-mode branch of `build_play_order`**

In `core/play_order.py`, find the class-mode branch (roughly lines 21–33). It currently looks like:

```python
    if mode == "class":
        sorted_by_timer = sorted(images, key=lambda i: i.timer)
        result = []
        for _timer, group_iter in groupby(sorted_by_timer, key=lambda i: i.timer):
            group = list(group_iter)
            pinned = [img for img in group if img.pinned]
            unpinned = [img for img in group if not img.pinned]
            result.extend(pinned + unpinned)
        return result
```

Replace with:

```python
    if mode == "class":
        return sorted(images, key=lambda i: i.timer)
```

`sorted` is stable, so same-timer images keep their original list order.

Also remove the `from itertools import groupby` import at the top of the file — no longer needed.

Full file after the change:

```python
"""Build play order for a Drawer session (pure function, no Qt).

Applies pinned-first ordering within tier groups in quick mode. Class mode
ignores the pin flag entirely and plays images in tier-ascending order,
list-order within each tier.
"""


def build_play_order(images, *, mode):
    """Return the list of ImageItem in the order the viewer should show them.

    Rules:
    - Quick mode: pinned images come first in pin order, then non-pinned in
      list order. One group (tier not used).
    - Class mode: tier groups sorted ascending by img.timer; list order
      within each tier. Pin flag is ignored.
    """
    if mode not in ("quick", "class"):
        raise ValueError(f"unknown mode: {mode!r}")
    if not images:
        return []

    if mode == "class":
        return sorted(images, key=lambda i: i.timer)

    # Quick mode: one group
    pinned = [img for img in images if img.pinned]
    unpinned = [img for img in images if not img.pinned]
    return pinned + unpinned
```

- [ ] **Step 4: Run tests to verify all pass**

Run: `python -m pytest tests/test_play_order.py -v`
Expected: all tests pass.

Also run the full suite to be sure no cross-file regression:

Run: `python -m pytest -q`
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add core/play_order.py tests/test_play_order.py
git commit -m "feat: class mode ignores pin flag in build_play_order

Simplifies the class-mode branch from 'group by timer, within each
group sort pinned-first' to just 'sort by timer'. sorted is stable,
so list order within a tier is naturally preserved.

Tests updated:
- test_class_multiple_pinned_across_different_tiers now expects list
  order within each tier (pin ignored).
- test_class_multiple_pinned_same_tier_preserve_order same.
- test_class_pinned_first_within_tier renamed to
  test_class_pin_flag_does_not_reorder_tier; kept as-is because list
  order already matched.
- Added test_class_mode_ignores_pin_flag as a regression for the
  invariant: class output must not depend on pin flag.

Quick mode unchanged.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Remove pin-skip guards in `ui/settings_window.py` timer-assignment loops

**Files:**
- Modify: `ui/settings_window.py`

Under the new model, every image gets a timer based on mode (quick → quick_timer; class → positional walk). The three places that currently skip pinned images need the skip removed.

- [ ] **Step 1: `_apply_timers_for_mode` quick branch — remove pin skip**

In `ui/settings_window.py`, find `_apply_timers_for_mode` (around lines 178–196). The quick branch currently looks like:

```python
    def _apply_timers_for_mode(self):
        """..."""
        if self._timer_panel.timer_mode == "quick":
            timer = self._timer_panel.get_timer_seconds()
            for img in self.images:
                if not getattr(img, "pinned", False):
                    img.timer = timer
        else:
            self._reapply_timers()
```

Remove the `if not getattr(...):` guard:

```python
    def _apply_timers_for_mode(self):
        """Assign per-image timers appropriate for the current mode.

        Quick mode: every image gets the current quick-mode timer. Pinned
        images also adapt (no more 'own timer' lock).
        Class mode: redistribute (may send some images to Reserve if budget
        is tight).
        """
        if self._timer_panel.timer_mode == "quick":
            timer = self._timer_panel.get_timer_seconds()
            for img in self.images:
                img.timer = timer
        else:
            self._reapply_timers()
```

- [ ] **Step 2: `_apply_class_timers` — remove pin skip**

Find `_apply_class_timers` (around lines 202–210). It currently looks like:

```python
    def _apply_class_timers(self):
        timers = groups_to_timers(self._timer_panel.class_groups)
        idx = 0
        for img in self.images:
            if getattr(img, "pinned", False):
                continue
            img.timer = timers[idx] if idx < len(timers) else 0
            idx += 1
```

Remove the pinned-skip:

```python
    def _apply_class_timers(self):
        timers = groups_to_timers(self._timer_panel.class_groups)
        for idx, img in enumerate(self.images):
            img.timer = timers[idx] if idx < len(timers) else 0
```

- [ ] **Step 3: `_start_slideshow` quick branch — remove pin skip**

Find `_start_slideshow` (around lines 691–705). The quick branch currently looks like:

```python
        mode = self._timer_panel.timer_mode
        session_limit = self._bottom_bar.get_session_limit()
        if mode == "quick":
            timer = self._timer_panel.get_timer_seconds()
            if session_limit is not None and timer > session_limit:
                return
            for img in self.images:
                if not img.pinned:
                    img.timer = timer
        elif mode == "class":
            self._apply_class_timers()
```

Remove the `if not img.pinned:` guard:

```python
        mode = self._timer_panel.timer_mode
        session_limit = self._bottom_bar.get_session_limit()
        if mode == "quick":
            timer = self._timer_panel.get_timer_seconds()
            if session_limit is not None and timer > session_limit:
                return
            for img in self.images:
                img.timer = timer
        elif mode == "class":
            self._apply_class_timers()
```

- [ ] **Step 4: Sanity check — imports + full test suite**

Run: `python -c "from ui.settings_window import SettingsWindow; print('OK')"`
Expected: prints `OK`.

Run: `python -m pytest -q`
Expected: all tests pass. Spec #1/#2 tests that use pinned-first in quick mode still pass (build_play_order in quick mode still does pinned-first; only the *timer assignment* stopped skipping pinned).

- [ ] **Step 5: Commit**

```bash
git add ui/settings_window.py
git commit -m "refactor: timer-assignment loops no longer skip pinned images

Three coupled changes in settings_window.py:
1. _apply_timers_for_mode quick branch: every image gets the
   quick-mode timer (was: only non-pinned).
2. _apply_class_timers: positional walk covers every image (was:
   idx advanced only on non-pinned).
3. _start_slideshow quick branch: same change as #1 for the
   session-start code path.

Pinned images now adapt to the current mode's timer. The 'stranded
pinned timer' edge case (e.g., pinned 15m image haunting a 1m quick
session) can no longer happen. Pin still drives play order in quick
mode via build_play_order's pinned-first logic; class mode already
ignores pin after task 1.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: `_on_shuffle_clicked` — class mode shuffles everything

**Files:**
- Modify: `ui/settings_window.py`

In quick mode, shuffling should still preserve pinned images at their positions (so they keep playing first). In class mode, pin is ignored, so there's no reason to preserve pinned positions — everything shuffles.

- [ ] **Step 1: Replace `_on_shuffle_clicked` with a mode-aware version**

Find `_on_shuffle_clicked` in `ui/settings_window.py` (around lines 633–652). Current code:

```python
    def _on_shuffle_clicked(self):
        """Shuffle button was clicked — reorder non-pinned images in place.

        In class mode, also rebuild the distribution so the editor preview
        reflects the new ordering. In quick mode, the new list order becomes
        the play order for the next session.
        """
        non_pinned_indices = [i for i, img in enumerate(self.images)
                              if not getattr(img, "pinned", False)]
        non_pinned = [self.images[i] for i in non_pinned_indices]
        random.shuffle(non_pinned)
        for target_i, img in zip(non_pinned_indices, non_pinned):
            self.images[target_i] = img

        self._apply_timers_for_mode()
        self._rebuild_editor_view()
```

Replace with:

```python
    def _on_shuffle_clicked(self):
        """Shuffle button was clicked — reorder images in place.

        Quick mode: shuffles non-pinned only. Pinned images stay at their
        current positions so they keep playing first.
        Class mode: shuffles every image (pin has no effect in class mode).
        """
        if self._timer_panel.timer_mode == "class":
            random.shuffle(self.images)
        else:
            non_pinned_indices = [i for i, img in enumerate(self.images)
                                  if not getattr(img, "pinned", False)]
            non_pinned = [self.images[i] for i in non_pinned_indices]
            random.shuffle(non_pinned)
            for target_i, img in zip(non_pinned_indices, non_pinned):
                self.images[target_i] = img

        self._apply_timers_for_mode()
        self._rebuild_editor_view()
```

- [ ] **Step 2: Sanity check**

Run: `python -c "from ui.settings_window import SettingsWindow; print('OK')"`
Expected: prints `OK`.

Run: `python -m pytest -q`
Expected: all tests pass.

- [ ] **Step 3: Commit**

```bash
git add ui/settings_window.py
git commit -m "feat: class-mode shuffle reshuffles every image

Quick mode still preserves pinned positions so they stay first. Class
mode has no pin concept, so there's nothing special to preserve —
random.shuffle on self.images directly.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: EditorPanel — add `timer_mode` awareness + mode-aware `_sort_group_items`

**Files:**
- Modify: `ui/editor_panel.py`
- Modify: `ui/image_editor_window.py`
- Modify: `ui/settings_window.py`

`EditorPanel` needs to know whether the user is in quick or class mode so it can behave differently for tier-group sorting (and, in Task 5, for context menu suppression). Add a constructor kwarg + a setter; the SettingsWindow keeps them in sync.

- [ ] **Step 1: EditorPanel accepts and stores `timer_mode`**

In `ui/editor_panel.py`, find the `EditorPanel.__init__` signature (around line 151). It currently looks like:

```python
    def __init__(self, images, theme, parent=None, view_mode="list",
                 collapsed_tiers=None, all_tier_timers=None):
```

Add a `timer_mode` parameter defaulting to `"quick"`:

```python
    def __init__(self, images, theme, parent=None, view_mode="list",
                 collapsed_tiers=None, all_tier_timers=None,
                 timer_mode="quick"):
```

Inside `__init__`, store it (near `self._view_mode = ...` around line 157):

```python
        self._timer_mode = timer_mode if timer_mode in ("quick", "class") else "quick"
```

Add a setter method somewhere near other setters — good location is immediately after `_set_view_mode` (around line 403+):

```python
    def set_timer_mode(self, mode):
        """Update the current timer mode ('quick' or 'class').

        SettingsWindow should call this whenever the mode changes so the
        editor can adjust its display (sort order, context menu)."""
        if mode not in ("quick", "class"):
            return
        if mode == self._timer_mode:
            return
        self._timer_mode = mode
        self._rebuild()
```

- [ ] **Step 2: `_sort_group_items` becomes mode-aware**

Currently `_sort_group_items` is a module-level function (around line 44). To access `self._timer_mode`, the call sites need access to the panel. Simplest approach: keep the module-level function for backward compat with tests that may reference it, but convert its body to accept a `pinned_first` bool, then have call sites pass `self._timer_mode == "quick"`.

Replace the module-level function:

```python
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

Then find the two call sites inside `EditorPanel` (around lines 491 and 575). Both currently look like:

```python
            items = _sort_group_items(items)
```

Update both to:

```python
            items = _sort_group_items(items, pinned_first=(self._timer_mode == "quick"))
```

- [ ] **Step 3: ImageEditorWindow forwards `timer_mode`**

In `ui/image_editor_window.py`, find the `ImageEditorWindow.__init__` signature (around line 24). Add a `timer_mode="quick"` parameter and store it as `self._timer_mode_init`:

```python
    def __init__(self, images, theme, parent=None, view_mode="list", timer_mode="quick"):
        super().__init__(parent)
        self._images_init = images
        self._view_mode_init = view_mode
        self._timer_mode_init = timer_mode
```

(Adjust to preserve whatever other fields were already being stored; don't delete anything — this is additive.)

In the EditorPanel construction (around line 95–97), pass the mode through. The call currently looks like:

```python
        self._panel = EditorPanel(
            self._images_init, self.theme, parent=self,
            view_mode=self._view_mode_init,
            shuffle=self._shuffle_init, collapsed_tiers=saved_collapsed,
            ...
        )
```

Wait — spec #2 already removed the `shuffle` kwarg, so check the actual current code before editing. The call should look approximately:

```python
        self._panel = EditorPanel(
            self._images_init, self.theme, parent=self,
            view_mode=self._view_mode_init,
            collapsed_tiers=saved_collapsed,
            all_tier_timers=saved_all_tiers,
        )
```

Add `timer_mode=self._timer_mode_init`:

```python
        self._panel = EditorPanel(
            self._images_init, self.theme, parent=self,
            view_mode=self._view_mode_init,
            collapsed_tiers=saved_collapsed,
            all_tier_timers=saved_all_tiers,
            timer_mode=self._timer_mode_init,
        )
```

Add a method to forward mode changes to the panel. Put it near the other ImageEditorWindow methods:

```python
    def set_timer_mode(self, mode):
        self._timer_mode_init = mode
        if self._panel is not None:
            self._panel.set_timer_mode(mode)
```

- [ ] **Step 4: SettingsWindow passes the current mode on creation and updates it on change**

In `ui/settings_window.py`, find where the editor is constructed (around line 616). It currently looks approximately:

```python
        self.editor = EditorPanel(
            self.images, self.theme, parent=self, view_mode=view)
```

Update to pass the current mode:

```python
        self.editor = EditorPanel(
            self.images, self.theme, parent=self, view_mode=view,
            timer_mode=self._timer_panel.timer_mode)
```

If the editor is instead constructed as an `ImageEditorWindow`, do the same with that constructor. (Check the file to confirm which path is in use.)

In `_on_timer_config_changed` (around lines 171–175), after the existing work, push the mode to the editor if it's open:

```python
    def _on_timer_config_changed(self):
        """TimerPanel changed mode, preset, or tiers — update images and summary."""
        self._apply_timers_for_mode()
        self._rebuild_editor_view()
        if self._editor_visible:
            self.editor.set_timer_mode(self._timer_panel.timer_mode)
```

- [ ] **Step 5: Sanity check + full test suite**

Run: `python -c "from ui.editor_panel import EditorPanel; from ui.image_editor_window import ImageEditorWindow; from ui.settings_window import SettingsWindow; print('OK')"`
Expected: prints `OK`.

Run: `python -m pytest -q`
Expected: all tests pass. `tests/test_pinned_sort.py` exercises the module-level `_sort_group_items` — the default arg `pinned_first=True` preserves its behavior, so those tests should continue to pass without change.

- [ ] **Step 6: Commit**

```bash
git add ui/editor_panel.py ui/image_editor_window.py ui/settings_window.py
git commit -m "feat: EditorPanel aware of timer_mode; sort drops pin-first in class

Threads timer_mode through EditorPanel, ImageEditorWindow, and
SettingsWindow. _sort_group_items gains a pinned_first kwarg (default
True for backward compat) and call sites pass mode == 'quick'.

In class mode the editor now shows images in list order within each
tier group — no pin-first reshuffle.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Remove "Move to group" submenu + suppress context menu in class mode

**Files:**
- Modify: `ui/editor_panel.py`

With move-to-group removed entirely and pin hidden in class mode, the per-image context menu has no useful actions in class mode and should not open. In quick mode, the menu retains just the Pin/Unpin toggle.

- [ ] **Step 1: Strip the Move-to-group submenu from `_build_img_menu`**

In `ui/editor_panel.py`, find `_build_img_menu` (around line 849). It currently looks like:

```python
    def _build_img_menu(self, img):
        """Build styled context menu with pin toggle and 'Move to...' submenu."""
        from PyQt6.QtWidgets import QMenu
        t = self.theme
        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu {{ background-color: {t.bg_button}; color: {t.text_primary}; "
            f"border: 1px solid {t.border}; font-size: {S.FONT_BUTTON}px; }}"
            f"QMenu::item:selected {{ background-color: {t.bg_active}; }}"
        )

        pinned = getattr(img, "pinned", False)
        pin_action = menu.addAction("Unpin" if pinned else "Pin to group")

        # "Move to..." submenu — all configured tiers + existing groups
        move_menu = menu.addMenu("Move to...")
        groups = self._group_by_timer()
        seen = set()
        for timer_val in sorted(self._all_tier_timers):
            if timer_val == img.timer:
                continue
            label = "Reserve" if timer_val == 0 else format_time(timer_val)
            act = move_menu.addAction(label)
            act.setData(timer_val)
            seen.add(timer_val)
        for timer_val in groups.keys():
            if timer_val in seen or timer_val == img.timer:
                continue
            label = "Reserve" if timer_val == 0 else format_time(timer_val)
            act = move_menu.addAction(label)
            act.setData(timer_val)
            seen.add(timer_val)
        if 0 not in seen and img.timer != 0:
            act = move_menu.addAction("Reserve")
            act.setData(0)

        return menu, pin_action
```

Replace with the simpler version — pin-only:

```python
    def _build_img_menu(self, img):
        """Build styled context menu with just a Pin/Unpin toggle."""
        from PyQt6.QtWidgets import QMenu
        t = self.theme
        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu {{ background-color: {t.bg_button}; color: {t.text_primary}; "
            f"border: 1px solid {t.border}; font-size: {S.FONT_BUTTON}px; }}"
            f"QMenu::item:selected {{ background-color: {t.bg_active}; }}"
        )
        pinned = getattr(img, "pinned", False)
        pin_action = menu.addAction("Unpin" if pinned else "Pin")
        return menu, pin_action
```

Also update the section-header comment above (line 846) from `# Context menus (pin / move to group)` to `# Context menus (pin only)`.

- [ ] **Step 2: Simplify `_handle_menu_action`**

The move-to-group branch is now dead code. Replace `_handle_menu_action` (around line 887) with:

```python
    def _handle_menu_action(self, img, action, pin_action):
        """Handle result from _build_img_menu. Returns True if something changed."""
        if action == pin_action:
            img.pinned = not getattr(img, "pinned", False)
            self._rebuild()
            self._emit()
            return True
        return False
```

- [ ] **Step 3: Suppress context menus in class mode**

Find `_show_context_menu` (around line 900) and `_show_tile_context_menu` (around line 912). Add an early-return guard at the top of each when the editor is in class mode.

`_show_context_menu`:
```python
    def _show_context_menu(self, pos, list_widget):
        if self._timer_mode == "class":
            return
        item = list_widget.itemAt(pos)
        if item is None:
            return
        idx = item.data(Qt.ItemDataRole.UserRole)
        if idx is None or idx >= len(self.images):
            return
        img = self.images[idx]
        menu, pin_action = self._build_img_menu(img)
        action = menu.exec(list_widget.mapToGlobal(pos))
        self._handle_menu_action(img, action, pin_action)
```

`_show_tile_context_menu`:
```python
    def _show_tile_context_menu(self, tile, global_pos):
        if self._timer_mode == "class":
            return
        idx = tile.property("img_idx")
        if idx is None or idx >= len(self.images):
            return
        img = self.images[idx]
        menu, pin_action = self._build_img_menu(img)
        action = menu.exec(global_pos)
        self._handle_menu_action(img, action, pin_action)
```

- [ ] **Step 4: Sanity check + full test suite**

Run: `python -c "from ui.editor_panel import EditorPanel; print('OK')"`
Expected: prints `OK`.

Run: `python -m pytest -q`
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add ui/editor_panel.py
git commit -m "feat: drop Move-to-group submenu; suppress class-mode context menu

Move-to-group was useful only under the old 'pinned locks a tier'
semantic — the next positional redistribute overwrites any manual
tier choice now, so the submenu has no effect. Removed entirely
along with its branch in _handle_menu_action.

In class mode the per-image context menu is empty (pin is hidden,
move-to-group is gone), so the right-click handlers early-return
before opening any menu. In quick mode the menu retains just the
Pin/Unpin action.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: Manual smoke test (for Oksana)

**Files:** none — user verification only.

Oksana runs this after the branch is pushed and before merging.

- [ ] **Step 1: Launch the app**

Run: `python main.py`

Load a session with 20+ images. (Drag a folder into the window if starting fresh.)

- [ ] **Step 2: Quick mode, pin behavior and timer adaptation**

1. Switch to quick mode. Set the quick timer to 30s.
2. Pin one image (right-click → Pin).
3. Start a session. Verify: pinned image plays first for 30s.
4. End session. Change quick timer preset to 2m.
5. Start a new session. Verify: pinned image plays first for **2m** (not 30s from before). The pinned image's timer adapted to the new preset.

- [ ] **Step 3: Switch to class mode — no pin UI, no move-to-group**

1. Switch to class mode with any tier selection.
2. Right-click on any image in the editor. Expected: **no context menu opens at all**.
3. Verify the editor shows images grouped by tier, with no pinned-first reordering within tiers — list order is preserved.

- [ ] **Step 4: Class-mode play order ignores pin**

1. Still in class mode, start a session. Verify: play order is tier-ascending, list-order-within-tier. The image you pinned in quick mode appears in its tier at its list-order position, with no special priority.

- [ ] **Step 5: Class-mode shuffle reshuffles everything**

1. Click the shuffle button. Verify: every image (including previously-pinned) moves around. Non-pinned and pinned shuffle together — no image is held in place.

- [ ] **Step 6: Switch back to quick mode — pin state preserved**

1. Switch back to quick mode. Verify: the image you pinned earlier is still shown as pinned. The pin flag survived the trip through class mode.
2. Start a session. Verify: pinned image plays first.

- [ ] **Step 7: Session restart preserves pin**

1. Close the app entirely. Reopen (`python main.py`). Load the same session.
2. Verify: the pin from step 2 is still there in quick mode.

- [ ] **Step 8: Report back**

If all six scenarios look right, report "looks good." Otherwise, describe what didn't look right (screenshots welcome).

---

## Self-review summary

- **Spec coverage:**
  - Quick mode pin UI visible, timer adapts → Task 2 (step 1, step 3)
  - Class mode pin hidden, flag ignored → Task 5 (context menu suppression) + Task 1 (build_play_order) + Task 2 (timer assignment)
  - Class-mode `_sort_group_items` no pin-first → Task 4 (mode-aware sort)
  - Move-to-group removed → Task 5 (submenu dropped)
  - Class-mode shuffle shuffles all → Task 3
  - Data persistence across modes → no code change needed; img.pinned stays on the dataclass
- **Placeholders:** none — every step has executable code and exact commands.
- **Type consistency:** `timer_mode` as "quick"|"class" string is used consistently across EditorPanel, ImageEditorWindow, and SettingsWindow. `_sort_group_items` gains a `pinned_first` bool parameter with a default that preserves backward-compatible behavior.
- **Out of scope:** drag-and-drop reordering (spec #4), pin visibility UX, auto-pin-on-move removal (resolved as a side effect of removing move-to-group).
