# Drop pin in class mode — Design

**Date:** 2026-04-18
**Status:** Approved (pending user spec review)
**Scope:** Remove the pin concept from class mode. Pin remains a quick-mode-only feature. In quick mode, pinned images adapt their timer to the current quick-mode timer instead of keeping their own.

## Problem

Across specs #1 and #2 we accumulated several pinning-related behaviors that never cohered into one mental model:

1. **Pinned images kept their own timer** across mode switches and tier changes. This led to "stranded" pinned images (e.g., a pinned 15m image appearing in a quick 1m session as a phantom 15m group in the editor).
2. **Pinning in class mode had weak semantics.** It guaranteed neither inclusion (pinned image could still end up in Reserve via positional walk) nor tier placement (positional walk assigned tier independent of pin). The pin flag mostly controlled "play first within tier" — a subtle priority that didn't match the user's mental model of "pin = include this for sure."
3. **Shuffle preservation of pin position + positional tier assignment** created a soft, position-dependent guarantee that was hard to explain.
4. **Move-to-group context menu** auto-pinned the image and set its timer — a side effect users didn't expect, documented in the auto-pin-on-move deferred feedback. Under this design, the submenu is removed entirely (see Code changes).

The original spec #3 idea was to add pinned-aware session budgeting (subtract pinned timers from the distribution budget). Through this brainstorming round, we concluded that spec was treating a symptom rather than the cause — the real fix is to simplify what pinning *means*.

## Decision

**Pin is a quick-mode-only concept.** It persists on the image data across mode switches (so users don't lose their pin state), but class mode ignores it entirely. In quick mode, pinned images adapt their timer to the current quick-mode timer (same as non-pinned). The only effect of pin is play-order priority in quick mode.

This discards the "pinned images keep their own timer" feature. Users who want "specific image for specific duration" use quick mode + set quick-mode timer + pin. Class mode is for tier-based randomized sessions; no per-image privileges.

### Rationale

- **Quick mode pin has a clear, strong semantic:** include this image, play it first, for the quick-mode timer. Matches the "ensure this plays, for this duration" user intent.
- **Class mode loses pin — and that's fine.** Class mode's point is tier-based structured randomness. If a user wants a specific image at a specific duration, they should use quick mode. Class mode doesn't need a per-image "please include this" control — that's what tier selection + non-tight session limits are for.
- **No more stranded timers.** Since quick mode resets pinned image timers to quick-mode timer on any mode-or-preset change, there's no more "pinned image with timer=900 in a 1m session" edge case.
- **No more pinned-aware budget math.** The original spec #3 complexity (subtract pinned from budget, block Start when pinned exceeds) dissolves. Existing spec #2 block-Start rules (`quick_timer > session_limit`, class-mode `playable` empty) remain sufficient.

## Out of scope

- Drag-and-drop reordering in the editor (spec #4).
- Broader UI redesign for the pin/move-to-group context menu.
- Any change to the ImageItem data shape. `img.pinned` stays as a simple bool.

## Data model

`ImageItem.pinned` remains as-is. Always persisted in session.json. Class mode reads it but never acts on it. Quick mode acts on it (play-order priority).

No migration needed. Existing saved sessions with pinned images load fine; the pin flag continues to affect behavior only when the session is started in quick mode.

## Behavior by mode

### Quick mode

- **Pin button visible and clickable** on every image in the editor.
- **Timer assignment:** every image (pinned or not) gets the current quick-mode timer on any relevant trigger (image add/remove, preset change, mode switch to quick, shuffle).
- **Play order:** pinned images play first, in pin order, followed by non-pinned in list order (or shuffled order if the user has clicked shuffle — the shuffle rework from spec #2 preserves pinned positions).
- **Editor display:** tier grouping is by `img.timer`. In quick mode all images share the same timer, so they land in one group. Pinned shown first within that group (matches play order).

### Class mode

- **Pin button hidden.** The editor's per-image context menu does not show a "Pin" / "Unpin" entry in class mode.
- **Context menu is empty in class mode** — with both pin and move-to-group gone, the right-click context menu on an image has no actions to show. The menu should simply not open in class mode.
- **Timer assignment:** every image (whether `pinned` is True or False) gets a timer from the positional walk in `_apply_class_timers`. The pin flag is not consulted.
- **Play order:** pure tier-ascending, list-order within each tier. No pin-priority sort.
- **Shuffle:** shuffles all images in `self.images` (no pinned-position preservation in class mode). This is different from quick mode, where shuffle preserves pinned positions.

## Code changes

### `ui/editor_panel.py`

1. **Remove the "Move to group" submenu entirely** from the context-menu builder (`_build_img_menu` or equivalent). Also remove the code path in `_handle_menu_action` that handled the tier-timer assignment (`img.timer = action.data(); img.pinned = True`). This submenu was useful only under the old "pinned = locks tier" semantic and has no role under this design.
2. **In class mode, suppress the context menu entirely.** With move-to-group removed and pin hidden in class mode, the menu has no actions to show. The right-click handler should early-return when `timer_mode == "class"`.
3. **In quick mode, the context menu contains just the Pin/Unpin action.** No code change here beyond whatever falls out of removing the move-to-group branch.
4. In `_sort_group_items` (used for editor display ordering within tier groups), make the behavior mode-aware: in class mode, skip the pinned-first sort — return items in their natural list order. In quick mode, keep the current pinned-first sort.

### `ui/settings_window.py`

1. **`_on_timer_config_changed`** (quick branch): remove the `if not getattr(img, "pinned", False)` guard. Every image gets the quick-mode timer.
2. **`_apply_class_timers`**: remove the `if getattr(img, "pinned", False): continue` skip. Every image participates in the positional walk.
3. **`_start_slideshow`** (quick branch): remove the `if not img.pinned` guard on the timer loop. Every image gets quick-mode timer.
4. **`_on_shuffle_clicked`**: when `timer_mode == "class"`, shuffle all images (not just non-pinned). Existing quick-mode behavior — preserving pinned positions — stays.

### `core/play_order.py`

1. In the class-mode branch of `build_play_order`, drop the pinned-first sort within each tier. Class mode becomes: group by timer (ascending), within each group preserve input list order. Quick-mode branch stays unchanged.

### Tests

- `tests/test_play_order.py`: remove or update class-mode tests that assert pinned-first within-tier behavior. The class-mode tests should now assert pure tier-ascending + list-order.
- Add a regression test: `test_class_mode_ignores_pinned_flag` — same image set with and without `pinned=True` produces identical play order in class mode.

## Edge cases

| Case | Behavior |
|------|----------|
| User pins images in quick mode, switches to class mode | Pin UI hidden. Pinned images appear in the editor like any other. No special play order. Flags remain `True` on the data. |
| User switches back to quick mode | Pin UI returns. Pinned images shown as pinned. Play first in quick mode. No state lost. |
| Saved session (`session.json`) has `pinned=True` images, loads in class mode | Flags loaded normally. Class mode ignores them. No error, no warning. |
| User somehow has `pinned=True` with `timer=0` (Reserve) | Same as any timer=0 image — filtered out of playback. Pin is irrelevant. |
| All images pinned, in quick mode | All get quick-mode timer, all play in pin order, no non-pinned left. Fine. |
| All images pinned, in class mode | Flags ignored. Same behavior as no pinned images — positional distribution. Fine. |
| User in class mode clicks shuffle | All images shuffled, including those with `pinned=True`. Editor rebuilds with new positions → new tier assignments. |
| User in quick mode, session limit 5m, quick timer 15m | Spec #2's "block if quick_timer > session_limit" rule fires. Start blocked. Pinned state irrelevant (can't start). |

## Testing plan

**Unit tests** (`tests/test_play_order.py`): updated as above.

**Manual smoke test** (for Oksana, post-implementation):

1. Launch app. Add 20+ images.
2. **Quick mode, pin behavior:** set quick timer to 30s. Pin one image. Start session. Verify pinned image plays first for 30s.
3. **Quick mode, preset change:** change quick timer to 2m. Verify editor shows all images (including pinned) in the 2m group. Start session. Verify pinned image plays first for 2m (not 30s from before).
4. **Switch to class mode:** tier selection any mix. Verify right-clicking an image shows no context menu at all (nothing to configure per-image in class mode).
5. **Class mode play order:** start session. Verify play order is tier-ascending, list-order-within-tier, regardless of any `pinned=True` images from earlier.
6. **Class mode shuffle:** click shuffle. Verify all images (including previously-pinned ones) reshuffle.
7. **Switch back to quick:** verify the image you pinned earlier is still pinned (pin UI state preserved). Start — pinned plays first.
8. **Persistence:** close and reopen app. Load prior session. Pin state preserved.

## Acceptance

- `img.pinned` data field is unchanged, persisted, and read consistently across modes.
- Quick mode: pinned image timer always matches current quick-mode timer; pinned plays first in play order.
- Class mode: `img.pinned` has no user-visible effect — not displayed, not ordered, not editable via UI.
- Editor context menu in class mode has no pin or move-to-group entries.
- Class-mode `build_play_order` output is invariant under pin-flag changes.
- All existing spec #1 and spec #2 tests pass (either unchanged or with pinned-related expectations relaxed for class mode).
- No regression in quick-mode pinning behavior.
