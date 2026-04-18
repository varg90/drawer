# Shuffle Coupling Decoupling — Design

**Date:** 2026-04-18
**Status:** Approved (pending user spec review)
**Scope:** Decouple class-mode shuffle from quick-mode order. Bundle a small class-mode simplification: disable delete and selection (add stays enabled). Quick-mode behavior is entirely unchanged.

## Problem

After specs #1–#4 shipped, both the quick-mode and class-mode editor views render from the same `self.images` list. Any reorder action (shuffle, drag-drop, pin toggle, delete) mutates that one list, so switching modes shows the other view with the same mutated order.

The destructive workflow Oksana raised:

1. User carefully arranges non-pinned images in quick mode — the order represents real time invested.
2. User switches to class mode and clicks shuffle once.
3. Class-mode shuffle does `random.shuffle(self.images)` — reorders the canonical list.
4. User switches back to quick mode. Their arrangement is gone. They redo the work.

Related incoherences in class mode (post spec #3/#4):
- **Delete** in class mode is semantically broken: the tile user removes is replaced by another shuffle-pool candidate the user may also dislike. Endless loop.
- **Selection** in class mode has no purpose (pin, drag, right-click menu, and now delete are all disabled) — clicking an image shows an accent frame that does nothing.

## Decision

**`self.images` is the canonical quick-mode list. Class-mode shuffle writes to a separate `_class_order` attribute that never touches `self.images`.** Add/delete are the only operations that affect *membership*; they patch both lists in lockstep. Everything else leaves `_class_order` intact — including quick-mode reorder, quick-mode shuffle, and pin toggles.

**Class mode becomes truly preview-only + shuffle + add + play.** Delete and selection are disabled. Add remains (it doesn't have the "delete → unwanted replacement → delete again" loop problem — it's purposeful).

### Data model

```python
# on SettingsWindow
self.images = []         # canonical, owned by quick mode
self._class_order = None # optional list[ImageItem], permutation of self.images
```

Invariant: when `_class_order is not None`, it contains exactly the same images as `self.images`, in a shuffled order.

### Lifecycle of `_class_order`

- **Class-mode shuffle:** `self._class_order = random.sample(self.images, len(self.images))`.
- **Add (either mode):** append new image(s) to `self.images` AND to `_class_order` if set.
- **Delete (quick mode only — class-mode delete is disabled):** remove from `self.images` AND from `_class_order` if set.
- **Reorder / shuffle / pin toggle in quick mode:** no effect on `_class_order` (same image set, both lists remain valid permutations of the same set).
- **Mode switches:** no effect.
- **Tier-config changes:** no effect on `_class_order`; `_apply_class_timers` rewrites `img.timer` on the shared `ImageItem` objects.
- **Session save/restore:** `_class_order` is not persisted; it resets to `None` on app restart.

### Class-mode behavior

What's allowed in class mode:
- **Shuffle** — writes to `_class_order`, doesn't touch `self.images`.
- **Add** — drag files from Explorer onto the editor or main window; appends to both lists.
- **Session start** — playback order is `_class_order or self.images`, passed through `build_play_order` with `mode="class"`.
- **Tier-config changes** — positional timer walk operates on `_class_order or self.images`.

What's disabled in class mode:
- **Delete** — `_delete_selected` early-returns; `_list_scroll` / `_grid_scroll` ignore Delete key effect because selection is empty.
- **Selection** — `QListWidget.setSelectionMode(NoSelection)` in class mode; `_on_tile_click` early-returns when `_timer_mode == "class"`; no accent frame appears.
- **Drag** — already disabled (spec #4).
- **Context menu** — already disabled (spec #3).
- **Pin** — already disabled (spec #3).

## Rationale

- **`_class_order` as a separate list is the simplest architecturally correct fix.** Quick mode owns `self.images` as the canonical order; class mode has its own private shuffled view. No cross-contamination. No two-source-of-truth sync logic beyond the add/delete append/filter.
- **Invalidating only on membership change, not on position change.** Quick-mode reorder and class-mode order are independent. Pin toggle is quick-mode-only semantics (class ignores pin). Their positions don't need to mirror each other — they're views of the same pool.
- **Disabling class-mode delete** acknowledges the "delete → random replacement → delete again" loop pattern and removes a semantically broken action.
- **Disabling class-mode selection** follows directly from delete being gone: with no drag, no context menu, no pin, no delete, selection was vestigial.
- **Keeping class-mode add** recognizes that add is purposeful (user knows what they're loading) and has no frustration loop — new material just joins the pool.

## Out of scope

- **Slot-machine class mode** (reintroduce pin + shuffle-keepers workflow in class mode, reversing spec #3). Raised during this brainstorm, parked as `project_slot_machine_class_mode.md` for a future spec.
- **Class-mode delete with confirmation or undo.** Not worth the complexity given delete has no useful semantic in the current class-mode model.
- **Persisting `_class_order` across app restarts.** Transient by design.
- **Memory of past class-mode shuffles (undo shuffle).** Each shuffle overwrites the previous one; no history.
- **Hint text on shuffle button.** Not needed once the coupling bug is fixed.

## Code changes

### `ui/settings_window.py`

1. **Add `self._class_order = None`** to `__init__`.

2. **`_on_shuffle_clicked`** — rewrite both branches:
   - **Class branch:** replace `random.shuffle(self.images)` with `self._class_order = random.sample(self.images, len(self.images))` (no mutation of `self.images`). Then `self._apply_timers_for_mode()` + `self._rebuild_editor_view()` as today.
   - **Quick branch:** unchanged logic (shuffle non-pinned within `self.images`). No `_class_order` touch here — quick-mode reorder doesn't affect class-mode membership.

3. **New helper `_sync_class_order_membership`** — call after any `self.images` mutation to keep `_class_order` consistent:
   ```python
   def _sync_class_order_membership(self):
       """Patch _class_order to mirror self.images membership (same set).
       Preserves relative shuffle order for surviving items. Appends new
       images at the end. No-op when _class_order is None."""
       if self._class_order is None:
           return
       current = set(id(img) for img in self.images)
       # Drop images no longer in self.images, preserve order for survivors.
       self._class_order = [img for img in self._class_order
                            if id(img) in current]
       # Append any new images (in self.images but not yet in _class_order).
       class_set = set(id(img) for img in self._class_order)
       for img in self.images:
           if id(img) not in class_set:
               self._class_order.append(img)
   ```

4. **`_on_editor_update`** — fires on editor-driven mutations (drag-drop or delete within the editor). Already does `self.images = list(images)`. Append a call to `self._sync_class_order_membership()` after that assignment. Drag-drop in quick mode preserves membership so the helper is a no-op; delete in the editor changes membership so the helper filters.

5. **`_on_images_changed`** — fires on add via drag-from-Explorer or the add-files / add-folder buttons. After the existing body, call `self._sync_class_order_membership()` to append the new images to `_class_order` if set.

6. **Any other mutation of `self.images`** (including the main-window `dropEvent` that routes to `_on_images_changed`, or any code path that directly mutates `self.images`) must call `_sync_class_order_membership()` afterward. Grep for `self.images` assignments / mutations to find these.

7. **`_rebuild_editor_view`** — pass the right list to editor:
   ```python
   def _rebuild_editor_view(self):
       self._update_summary()
       if self._editor_visible:
           mode = self._timer_panel.timer_mode
           if mode == "class" and self._class_order is not None:
               self.editor.refresh(self._class_order)
           else:
               self.editor.refresh(self.images)
   ```

8. **`_start_slideshow`** — class branch uses `_class_order or self.images` as the source list for `_apply_class_timers` and `build_play_order`.

9. **`_apply_class_timers`** — walk `_class_order or self.images`:
   ```python
   def _apply_class_timers(self):
       timers = groups_to_timers(self._timer_panel.class_groups)
       source = self._class_order if self._class_order is not None else self.images
       for idx, img in enumerate(source):
           img.timer = timers[idx] if idx < len(timers) else 0
   ```

10. **External file drop onto main window** (existing `dropEvent` in `SettingsWindow`): continues to add via `_on_images_changed`, which now syncs `_class_order`. No class-mode block at this level — add is allowed in both modes.

### `ui/editor_panel.py`

11. **`_on_tile_click`** — early-return when `self._timer_mode == "class"`:
    ```python
    def _on_tile_click(self, lbl, ctrl, shift=False):
        if self._timer_mode == "class":
            return
        # existing logic
    ```

12. **`_rebuild_list`** — `SelectionMode.NoSelection` in class mode:
    ```python
    if self._timer_mode == "quick":
        lw.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
    else:
        lw.setSelectionMode(QListWidget.SelectionMode.NoSelection)
    ```

13. **`_delete_selected`** — defensive early-return in class mode (belt-and-suspenders with no-selection):
    ```python
    def _delete_selected(self):
        if self._timer_mode == "class":
            return
        # existing logic
    ```

14. **External file drop on editor** (`_drag_enter` / `_drag_move` / `_drop_event`): no change — URL drops still accepted in both modes (add works in class).

### No change to

- `core/play_order.py` — class-mode play order already uses list-order-within-tier after spec #3.
- `core/models.py` — `ImageItem` shape unchanged.
- `core/session.py` — `_class_order` not persisted.

## Edge cases

| Case | Behavior |
|------|----------|
| Class shuffle → switch to quick | Quick shows `self.images` (untouched). |
| Class shuffle → switch back to class | Still shows `_class_order`. |
| Quick-mode reorder or shuffle or pin toggle | `_class_order` unchanged; survives. |
| Quick-mode delete | Image removed from `self.images` AND `_class_order` (if set). Rest of class shuffle preserved. |
| Add image (either mode) | Appended to `self.images` AND `_class_order` (if set). New image lands at end of class-mode tier distribution. |
| Class-mode shuffle repeatedly | `_class_order` overwritten each click. No history. |
| Session start in class, `_class_order` set | Playback uses `_class_order`. |
| Session start in class, `_class_order` unset | Playback uses `self.images` (pristine tier order). |
| TimerPanel tier config changes with `_class_order` set | `_class_order` preserved; `_apply_class_timers` rewrites timers via positional walk on `_class_order`. |
| Class-mode selection attempt (click, Ctrl-click, Shift-click) | No accent frame. `_on_tile_click` early-returns. List widgets use `NoSelection`. |
| Class-mode Delete key | No-op (no selection). `_delete_selected` also early-returns defensively. |
| Class-mode external file drop | Accepted. Appends to both lists. |
| App restart | `_class_order` starts `None`. User re-shuffles if desired. |
| Mode switch mid-drag | Not reachable (drag blocks event loop). |

## Testing plan

**No new unit tests.** The logic is shallow: `random.sample`, list append, list filter. Existing 175 tests continue to pass. A helper like `_sync_class_order_membership` could be unit-tested in isolation, but it's a ~10-line function with obvious behavior; manual verification suffices.

**Manual smoke test** (Oksana, post-implementation):

1. Quick mode: reorder non-pinned images into a specific arrangement. Note the top 3 tiles' order.
2. Switch to class mode. Click shuffle. Verify tier groups reshuffle.
3. Switch back to quick mode. Verify the arrangement from step 1 is preserved.
4. Switch to class mode again. Verify the shuffle from step 2 is still in place.
5. Click shuffle again in class mode. Verify a new tier distribution.
6. Start a session in class mode. Verify playback order reflects the shuffle.
7. Return from session. Still class mode. Verify the shuffle is still visible in the editor.
8. Switch to quick mode, delete one image. Verify class mode (on next switch) no longer includes that image but keeps the rest of the shuffle.
9. In quick mode, drag a non-pinned tile to a new position. Verify class mode (on next switch) still shows the original shuffle — quick-mode reorder doesn't disturb class.
10. Drag new files from Explorer onto the class-mode editor. Verify they appear at the bottom of the class-mode tier distribution.
11. In class mode: click an image. Verify no accent frame appears (selection disabled).
12. In class mode: press Delete. Verify nothing happens.
13. In class mode: try the ctrl-click / shift-click pattern. Verify all are no-ops.

## Acceptance

- Class-mode shuffle no longer mutates `self.images`. Quick-mode order fully preserved across class-mode shuffle cycles.
- Quick-mode reorder, shuffle, and pin toggle all leave `_class_order` intact.
- Add in either mode appends to both lists; delete in quick removes from both.
- Class-mode selection visuals never appear.
- Class-mode delete (via key, menu, or any path) is a no-op.
- External file drops continue to work from both modes.
- Session playback in class mode respects `_class_order` when set.
- All existing tests (175) continue to pass.
