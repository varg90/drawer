# Shuffle Coupling Decoupling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Decouple class-mode shuffle from quick-mode order. Class mode gets its own `_class_order` list; `self.images` stays as canonical quick-mode truth. Bundle: disable class-mode selection + delete (add stays).

**Architecture:** A single optional `_class_order` attribute on `SettingsWindow`, overwritten by class-mode shuffle and synced for membership on add/delete. A pure-Python helper handles the membership sync so it's unit-testable. Mode-aware code paths in `SettingsWindow` and `EditorPanel` select the right list at display and playback time.

**Tech Stack:** Python 3.14, PyQt6, pytest. Logic is mostly list operations; no new dependencies.

**Spec:** `docs/superpowers/specs/2026-04-18-shuffle-coupling-design.md`

---

## File Structure

- **Create:** `tests/test_class_order_sync.py` — unit tests for the pure-Python sync helper.
- **Modify:** `ui/settings_window.py` — all `_class_order` state, lifecycle, and mode-aware plumbing.
- **Modify:** `ui/editor_panel.py` — disable selection + delete in class mode.
- **No change:** `core/play_order.py`, `core/models.py`, `ui/image_editor_window.py`, `core/session.py`.

---

### Task 1: Pure helper + tests (TDD)

**Files:**
- Create: `tests/test_class_order_sync.py`
- Modify: `ui/settings_window.py` (add one module-level function)

A module-level pure function that patches `_class_order` to mirror `self.images` membership. Unit-testable without Qt.

- [ ] **Step 1: Write failing tests**

Create `tests/test_class_order_sync.py`:

```python
"""Unit tests for the _class_order membership sync helper."""

from core.models import ImageItem
from ui.settings_window import _sync_class_order_to_images


def _img(path, timer=60, pinned=False):
    return ImageItem(path=path, timer=timer, pinned=pinned)


def test_none_passthrough():
    """When class_order is None, return None (no shuffle active)."""
    images = [_img("a"), _img("b")]
    assert _sync_class_order_to_images(None, images) is None


def test_same_membership_preserves_order():
    """Both lists contain the same set → class_order order is kept."""
    a, b, c = _img("a"), _img("b"), _img("c")
    images = [a, b, c]
    class_order = [c, a, b]  # some shuffle
    result = _sync_class_order_to_images(class_order, images)
    assert result == [c, a, b]


def test_deleted_image_dropped():
    """An image present in class_order but missing from images is filtered out."""
    a, b, c = _img("a"), _img("b"), _img("c")
    images = [a, c]  # b was deleted
    class_order = [c, b, a]
    result = _sync_class_order_to_images(class_order, images)
    assert result == [c, a]


def test_added_image_appended():
    """An image in images but not yet in class_order is appended at the end."""
    a, b, c = _img("a"), _img("b"), _img("c")
    images = [a, b, c]  # c was just added
    class_order = [b, a]
    result = _sync_class_order_to_images(class_order, images)
    assert result == [b, a, c]


def test_combined_add_and_delete():
    """Mixed: one deleted, one added. Survivors keep order, new at end."""
    a, b, c, d = _img("a"), _img("b"), _img("c"), _img("d")
    images = [a, c, d]  # b deleted, d added
    class_order = [b, c, a]
    result = _sync_class_order_to_images(class_order, images)
    assert result == [c, a, d]


def test_multiple_added_appended_in_images_order():
    """Two new images both get appended in self.images order."""
    a, b, c, d = _img("a"), _img("b"), _img("c"), _img("d")
    images = [a, b, c, d]  # c and d just added
    class_order = [b, a]
    result = _sync_class_order_to_images(class_order, images)
    assert result == [b, a, c, d]


def test_empty_images():
    """Empty images → empty class_order."""
    a, b = _img("a"), _img("b")
    result = _sync_class_order_to_images([a, b], [])
    assert result == []


def test_empty_class_order_populates_from_images():
    """Empty class_order with a non-empty images list appends all images."""
    a, b = _img("a"), _img("b")
    result = _sync_class_order_to_images([], [a, b])
    assert result == [a, b]


def test_preserves_item_identity_not_value():
    """Equal-by-value but distinct objects are tracked by identity (id())."""
    a1 = _img("a")
    a2 = _img("a")  # same path, different object
    images = [a2]
    class_order = [a1]
    result = _sync_class_order_to_images(class_order, images)
    # a1 not in images (by id), a2 is; so result should be [a2]
    assert result == [a2]
    assert result[0] is a2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_class_order_sync.py -v`
Expected: ImportError — `_sync_class_order_to_images` doesn't exist yet.

- [ ] **Step 3: Add helper to `ui/settings_window.py`**

In `ui/settings_window.py`, add the module-level function near the top (after imports, before `_InsetPanel` class at line 31):

```python
def _sync_class_order_to_images(class_order, images):
    """Return a class-mode order list that mirrors the membership of `images`.

    - Returns None when `class_order` is None (no shuffle active).
    - Keeps the relative order of surviving items.
    - Filters out items no longer in `images`.
    - Appends new items from `images` at the end, in `images` order.

    Uses id()-based identity: `ImageItem` equality may match on path while
    distinct objects live in each list.
    """
    if class_order is None:
        return None
    current = set(id(img) for img in images)
    survived = [img for img in class_order if id(img) in current]
    survived_set = set(id(img) for img in survived)
    for img in images:
        if id(img) not in survived_set:
            survived.append(img)
    return survived
```

- [ ] **Step 4: Run tests — all pass**

Run: `python -m pytest tests/test_class_order_sync.py -v`
Expected: all 9 tests pass.

Then the full suite: `python -m pytest -q`
Expected: no regressions (175 existing + 9 new = 184 total).

- [ ] **Step 5: Commit**

```bash
git add ui/settings_window.py tests/test_class_order_sync.py
git commit -m "$(cat <<'EOF'
feat: add _sync_class_order_to_images pure helper + tests

Module-level helper that mirrors the class-mode order list to
self.images membership: preserves relative order for survivors,
filters deleted, appends new at end. Uses id()-based identity so
path-equal but distinct ImageItem objects don't get conflated.

Unit tests cover None passthrough, add/delete in isolation and
combined, empty cases, and identity-vs-value semantics.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Add `_class_order` state + class-mode shuffle rewrite

**Files:**
- Modify: `ui/settings_window.py`

Add the `_class_order` attribute to `SettingsWindow.__init__` and rewrite the class branch of `_on_shuffle_clicked` to target it instead of `self.images`.

- [ ] **Step 1: Initialize `_class_order` in `__init__`**

Find `self.images = []` in `SettingsWindow.__init__` (line 69). After that line, add:

```python
        self.images = []
        self._class_order = None  # class-mode shuffled view; None = pristine tier order
```

- [ ] **Step 2: Rewrite class branch of `_on_shuffle_clicked`**

Find `_on_shuffle_clicked` (around line 628). Current class branch:

```python
        if self._timer_panel.timer_mode == "class":
            random.shuffle(self.images)
```

Replace with:

```python
        if self._timer_panel.timer_mode == "class":
            if not self.images:
                return
            self._class_order = random.sample(self.images, len(self.images))
```

The quick branch (non-pinned in-place reshuffle) stays unchanged.

- [ ] **Step 3: Sanity check**

Run: `python -c "from ui.settings_window import SettingsWindow; print('OK')"` → `OK`.
Run: `python -m pytest -q` → all 184 pass.

- [ ] **Step 4: Commit**

```bash
git add ui/settings_window.py
git commit -m "$(cat <<'EOF'
feat: class-mode shuffle writes to _class_order, leaves self.images alone

Introduces self._class_order = None on SettingsWindow. Class-mode
shuffle now does random.sample(self.images, ...) into _class_order
instead of mutating self.images in place. Quick-mode shuffle
unchanged. Downstream plumbing (_rebuild_editor_view, _apply_class_
timers, _start_slideshow) still reads self.images — those are updated
in subsequent tasks; this commit is behaviorally equivalent to
pre-shuffle state for class mode (shuffle appears to do nothing
visibly) until Task 4 wires _class_order into rendering.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Sync `_class_order` on self.images mutations

**Files:**
- Modify: `ui/settings_window.py`

Every place `self.images` is mutated must also sync `_class_order` so the membership invariant holds. Add `_sync_class_order_membership` as an instance method and call it from the mutation sites.

- [ ] **Step 1: Add `_sync_class_order_membership` instance method**

In `ui/settings_window.py`, inside the `SettingsWindow` class, add a small instance method near `_reapply_timers` (around line 209):

```python
    def _sync_class_order_membership(self):
        """Patch _class_order to mirror self.images membership. Call after
        any self.images mutation. No-op when _class_order is None."""
        self._class_order = _sync_class_order_to_images(
            self._class_order, self.images,
        )
```

- [ ] **Step 2: Sync in `_on_editor_update`**

Find `_on_editor_update` (line 648). Current:

```python
    def _on_editor_update(self, images):
        self.images = list(images)
        before = [img.timer for img in self.images]
        self._apply_timers_for_mode()
        self._update_summary()
        # Skip the editor refresh unless timers actually changed (quick-mode
        # reorders with no pin-state change produce no timer delta).
        if any(img.timer != t for img, t in zip(self.images, before)):
            self.editor.refresh(self.images)
```

Insert the sync call right after `self.images = list(images)`:

```python
    def _on_editor_update(self, images):
        self.images = list(images)
        self._sync_class_order_membership()
        before = [img.timer for img in self.images]
        self._apply_timers_for_mode()
        self._update_summary()
        if any(img.timer != t for img, t in zip(self.images, before)):
            self.editor.refresh(self.images)
```

- [ ] **Step 3: Sync in `_on_images_changed`**

Find `_on_images_changed` (line 595). Current:

```python
    def _on_images_changed(self):
        self._reapply_timers()
        self._update_summary()
        self.images_changed.emit()
        if self._editor_visible:
            self.editor.refresh(self.images)
```

Insert the sync call at the very start (before `_reapply_timers`, which can mutate timers on the ImageItems but not membership):

```python
    def _on_images_changed(self):
        self._sync_class_order_membership()
        self._reapply_timers()
        self._update_summary()
        self.images_changed.emit()
        if self._editor_visible:
            self.editor.refresh(self.images)
```

- [ ] **Step 4: Sync in `_restore_session`**

Find `_restore_session` — the lines that populate `self.images` from saved data (around line 746):

```python
        self.images = [ImageItem.from_dict(d) for d in images_data]
        self.images = [img for img in self.images if os.path.isfile(img.path)]
```

After these two lines, add:

```python
        self._class_order = None  # not persisted; reset on restore
```

(This is a reset rather than a sync because `_class_order` is not saved to session.json; it starts `None` on every app start.)

- [ ] **Step 5: Sanity check + commit**

Run: `python -c "from ui.settings_window import SettingsWindow; print('OK')"` → `OK`.
Run: `python -m pytest -q` → all 184 pass.

```bash
git add ui/settings_window.py
git commit -m "$(cat <<'EOF'
feat: sync _class_order on self.images mutations

New _sync_class_order_membership instance method wraps the pure helper.
Called from:
- _on_editor_update (drag-drop or delete via editor)
- _on_images_changed (add via drag-from-Explorer, add-files,
  add-folder, main-window drop)
- _restore_session resets _class_order to None (it's transient).

Invariant: when _class_order is not None, it's a permutation of
self.images.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Thread `_class_order` through display + playback

**Files:**
- Modify: `ui/settings_window.py`

`_rebuild_editor_view`, `_apply_class_timers`, and `_start_slideshow` must read from `_class_order or self.images` when in class mode so the shuffle becomes visible and plays in that order.

- [ ] **Step 1: Update `_rebuild_editor_view`**

Find `_rebuild_editor_view` (line 198):

```python
    def _rebuild_editor_view(self):
        """Refresh summary and, if the editor is open, re-render + sync tiers."""
        self._update_summary()
        if self._editor_visible:
            self.editor.refresh(self.images)
```

Replace with:

```python
    def _rebuild_editor_view(self):
        """Refresh summary and, if the editor is open, re-render + sync tiers."""
        self._update_summary()
        if self._editor_visible:
            mode = self._timer_panel.timer_mode
            display_list = (self._class_order
                            if mode == "class" and self._class_order is not None
                            else self.images)
            self.editor.refresh(display_list)
```

- [ ] **Step 2: Update `_apply_class_timers`**

Find `_apply_class_timers` (line 204):

```python
    def _apply_class_timers(self):
        timers = groups_to_timers(self._timer_panel.class_groups)
        for idx, img in enumerate(self.images):
            img.timer = timers[idx] if idx < len(timers) else 0
```

Replace with:

```python
    def _apply_class_timers(self):
        """Assign timers via positional walk. Uses _class_order when set so
        the shuffle decides tier assignment; falls back to self.images."""
        timers = groups_to_timers(self._timer_panel.class_groups)
        source = self._class_order if self._class_order is not None else self.images
        for idx, img in enumerate(source):
            img.timer = timers[idx] if idx < len(timers) else 0
```

- [ ] **Step 3: Update `_start_slideshow` class branch**

Find `_start_slideshow` (line 684). The class branch reads `self.images`:

```python
        if mode == "class":
            playable = [img for img in self.images if img.timer > 0]
            if not playable:
                return  # all images overflowed to Reserve, nothing to play
            show_images = build_play_order(playable, mode=mode)
```

Replace with:

```python
        if mode == "class":
            source = self._class_order if self._class_order is not None else self.images
            playable = [img for img in source if img.timer > 0]
            if not playable:
                return  # all images overflowed to Reserve, nothing to play
            show_images = build_play_order(playable, mode=mode)
```

The quick branch (`for img in self.images: img.timer = timer` then `build_play_order(self.images, mode=mode)`) stays unchanged — quick mode never reads `_class_order`.

- [ ] **Step 4: Sanity check + commit**

Run: `python -c "from ui.settings_window import SettingsWindow; print('OK')"` → `OK`.
Run: `python -m pytest -q` → all 184 pass.

```bash
git add ui/settings_window.py
git commit -m "$(cat <<'EOF'
feat: class-mode display + playback read from _class_order when set

Three coupled changes in settings_window.py:
- _rebuild_editor_view: in class mode with _class_order set, refresh
  editor with the shuffled list instead of self.images.
- _apply_class_timers: positional walk uses _class_order (or
  self.images fallback) to decide which image goes into which tier.
- _start_slideshow class branch: playable pool and play order derived
  from _class_order (or self.images).

Quick mode still reads self.images exclusively. Combined with Task 2
(class shuffle writes to _class_order), the end-to-end decoupling is
now in place: quick-mode arrangement survives class-mode shuffle.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Disable class-mode selection + delete

**Files:**
- Modify: `ui/editor_panel.py`

Class mode is now preview-only + shuffle + add (selection and delete have no purpose). Make selection and delete no-ops in class mode.

- [ ] **Step 1: Early-return in `_on_tile_click` for class mode**

Find `_on_tile_click` in `ui/editor_panel.py` (line 1262). It currently starts by checking shift + last_clicked_tile. At the top, add a class-mode guard:

```python
    def _on_tile_click(self, lbl, ctrl, shift=False):
        if self._timer_mode == "class":
            return
        if shift and self._last_clicked_tile is not None:
            # ... existing body
```

(Exact insert: a single `if self._timer_mode == "class": return` as the first statement of the method body.)

- [ ] **Step 2: `NoSelection` on list widgets in class mode**

Find `_rebuild_list` (line 875). The ExtendedSelection line is at 925:

```python
            lw.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
```

Replace with:

```python
            if self._timer_mode == "quick":
                lw.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
            else:
                lw.setSelectionMode(QListWidget.SelectionMode.NoSelection)
```

- [ ] **Step 3: Defensive early-return in `_delete_selected`**

Find `_delete_selected` (line 1511). At the top of the method, add:

```python
    def _delete_selected(self):
        if self._timer_mode == "class":
            return
        # ... existing body
```

(Selection will be empty in class mode after steps 1–2, so `_delete_selected` would already be a no-op via the "nothing to delete" path. This guard makes the intent explicit and protects against any code path we missed.)

- [ ] **Step 4: Sanity check + commit**

Run: `python -c "from ui.editor_panel import EditorPanel; print('OK')"` → `OK`.
Run: `python -m pytest -q` → all 184 pass.

```bash
git add ui/editor_panel.py
git commit -m "$(cat <<'EOF'
feat: disable selection + delete in class mode

Class mode is now preview-only + shuffle + add. Selection (accent
frame on click) and delete (Delete key, bulk selection) have no
useful semantic once pin/drag/context-menu/delete are all gone.

- _on_tile_click: early-return when _timer_mode == "class".
- _rebuild_list: NoSelection on list widgets in class mode; quick
  keeps ExtendedSelection.
- _delete_selected: defensive class-mode guard.

Add in class mode still works (external file drops accepted, add
buttons functional; _on_images_changed syncs _class_order).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Manual smoke test (for Oksana)

**Files:** none — user verification only.

Runs after the branch is pushed. Verifies the end-to-end decoupling + the class-mode restrictions.

- [ ] **Step 1: Launch the app**

Run: `python main.py`
Load a session with 15+ images.

- [ ] **Step 2: Quick-mode arrangement preserved across class-mode shuffle**

1. In quick mode, drag a non-pinned tile to a new position (or reorder multiple tiles). Note the top 3 tiles' order.
2. Switch to class mode. Click shuffle. Verify tier groups reshuffle visibly.
3. Switch back to quick mode. Verify the arrangement from step 1 is preserved — tiles in the same positions as before.

- [ ] **Step 3: Class-mode shuffle persists across mode switch**

1. Still in quick mode. Switch to class mode again. Verify the shuffle from the previous step is still in place (tier contents match the last shuffle).
2. Click shuffle again. Verify a different distribution.
3. Start a session in class mode. Verify playback order reflects the current shuffle.

- [ ] **Step 4: Quick-mode reorder doesn't disturb class-mode shuffle**

1. Return to quick mode. Reorder non-pinned tiles (drag or shuffle).
2. Switch to class mode. Verify the existing shuffle is still in place — the quick-mode reorder did NOT reset it.

- [ ] **Step 5: Delete in quick mode updates class-mode view**

1. In quick mode, delete one non-pinned image (select, press Delete).
2. Switch to class mode. Verify that image is no longer in any tier. The rest of the class-mode shuffle is preserved.

- [ ] **Step 6: Add in class mode appends**

1. Still in class mode. Drag new files from Windows Explorer onto the editor. Verify:
   - Files are added to the session.
   - New tiles appear at the bottom of whatever tier the positional walk assigns them.
   - The existing shuffle is otherwise unchanged.

- [ ] **Step 7: Class-mode selection is disabled**

1. In class mode, click on a tile. Verify: no accent frame appears.
2. Ctrl-click another tile. Verify: still no selection visuals.
3. Press Delete. Verify: nothing happens.

- [ ] **Step 8: Right-click in class mode still does nothing (existing behavior)**

1. Right-click a tile in class mode. Verify: no context menu opens.

- [ ] **Step 9: App restart resets `_class_order`**

1. With a class-mode shuffle active, close the app completely.
2. Reopen (`python main.py`). Load the same session.
3. Switch to class mode. Verify: tier groups show the pristine (list-order-within-tier) distribution. The previous shuffle is NOT restored.
4. Click shuffle. Verify: a fresh shuffle is produced.

- [ ] **Step 10: Report**

If all steps pass, report "looks good." Otherwise describe what broke (screenshots welcome).

---

## Self-review summary

- **Spec coverage:**
  - `_class_order` state + pure helper → Task 1
  - Class-mode shuffle writes to `_class_order` → Task 2
  - Add/delete sync, restore reset → Task 3
  - Display + playback read from `_class_order` → Task 4
  - Class-mode selection + delete disabled → Task 5
  - Quick-mode behavior unchanged → preserved across all tasks (all edits are additive or mode-gated)

- **Placeholders:** none — every step has executable code and exact commands.

- **Type consistency:** `_class_order` is consistently typed as `list[ImageItem] | None` across `__init__`, shuffle, sync, and readers. Helper function `_sync_class_order_to_images` has one signature everywhere it's called (via the `_sync_class_order_membership` instance wrapper).

- **Out of scope (tracked in memory):**
  - Slot-machine class mode — `project_slot_machine_class_mode.md`.
  - Zoom slider persistence bug — `project_zoom_persistence.md`.
