# Pinned-first Play Order — Design

**Date:** 2026-04-17
**Status:** Approved (pending user spec review)
**Scope:** Play-order only. Does not change auto-distribute, tier assignment, or the editor UI.

## Problem

When a session starts, pinned images are not prioritized:

- **Quick mode with shuffle on:** `settings_window._start_slideshow` currently builds `show_images = unpinned + pinned`, so pinned play **last**. This is the opposite of user expectation.
- **Quick mode with shuffle off:** order follows the underlying `self.images` list. The editor panel's pinned-first sort only affects display within tier groups; it does not reorder the backing list. A pinned image can end up anywhere.
- **Class mode:** images are sorted ascending by timer at the end of `_start_slideshow` (line 688). A pinned image in the 15m tier plays after all 30s / 1m / 5m tier images, regardless of pinning.

Use case driving this change: user pins one image they want to see in a given session (e.g., a long-pose 15m reference), and wants the pinned image to lead its tier group, not be scattered or last.

## Goal

Pinned images always play first *within their tier group*, in the order they were pinned. Non-pinned images follow.

In **quick mode** all images share one timer, so this is effectively one group: pinned first, rest after.
In **class mode** tier groups still play shortest-to-longest; within each tier, pinned first.

Explicitly **out of scope** (tracked as follow-up specs):

- Session-aware auto-distribute (independent pre-existing bug: auto-distribute can produce total duration far exceeding session limit)
- Pinned-aware auto-distribute (reserving tier slots for pinned images in the time budget)
- Cross-tier drag-and-drop in the editor

## Rules

1. **Pinned images always come before non-pinned** within the same tier group.
2. **Pinned images preserve their pin order.** No shuffling within the pinned group, even when shuffle is on. Rationale: a single pinned image should land deterministically first; reordering among pinned would surprise the user. The editor list already preserves pin order (`test_pinned_sort_preserves_order`), so this matches existing behavior.
3. **Non-pinned images** follow the shuffle setting:
   - `shuffle=True` → `random.shuffle` within the tier
   - `shuffle=False` → natural list order (order in `self.images`) within the tier
4. **Tier order in class mode** stays ascending by timer (30s → 1m → 5m → ...). Pinning does *not* let an image jump tiers.
5. **Empty image list** → empty play order. No change.

## Architecture

### New pure function

**File:** `core/play_order.py` (new)

```python
def build_play_order(images, *, shuffle, mode):
    """Return the list of ImageItem in the order the viewer should show them.

    Args:
        images: list[ImageItem] with .timer already assigned by caller.
        shuffle: bool — shuffle non-pinned images within each tier.
        mode: "quick" | "class" — class groups by timer; quick is one group.

    Rules: pinned-first within each tier group (pin order preserved),
    non-pinned follow (shuffled or natural). Tiers play ascending by timer
    in class mode.
    """
```

**No Qt imports.** Pure Python. Lives in `core/` alongside `class_mode.py`, `models.py`.

This is approach B from brainstorming: extracting the rule out of the UI layer makes it unit-testable without a Qt window and creates a clean seam for future play-order rules (spec #3 will extend this function).

### Call-site change

**File:** `ui/settings_window.py`, method `_start_slideshow` (lines 660-706).

Today (lines 679-688):

```python
if self._shuffle:
    pinned = [img for img in self.images if img.pinned]
    unpinned = [img for img in self.images if not img.pinned]
    random.shuffle(unpinned)
    show_images = unpinned + pinned
else:
    show_images = list(self.images)

if mode == "class" and self._timer_panel.class_groups:
    show_images.sort(key=lambda img: img.timer)
```

After:

```python
from core.play_order import build_play_order
show_images = build_play_order(self.images, shuffle=self._shuffle, mode=mode)
```

Timer assignment (lines 665-677) stays exactly as-is — it runs before `build_play_order` and is a separate concern (which timer each image gets, not which order they play in).

Everything downstream of `show_images` is untouched: the viewer settings dict, `ViewerWindow(...)` construction, post-close handling.

### Dropped behavior

Removing the class-mode `show_images.sort(key=lambda img: img.timer)` at line 688. `build_play_order` handles tier ordering internally and respects pinned-first within each tier. The external sort was what caused pinned 15m images to play after all shorter tiers regardless of pinning.

## Edge cases

| Case | Behavior |
|------|----------|
| No pinned images, shuffle off | Identity: natural list order. No behavioral change vs. today. |
| No pinned images, shuffle on | All images shuffled. Same outcome as today; implementation moves from UI to pure function. |
| One pinned image, shuffle on (quick mode) | Pinned first, rest shuffled after. |
| Multiple pinned, shuffle on (quick mode) | All pinned first in pin order, rest shuffled after. |
| All images pinned | Pin order, no shuffle. |
| Class mode, pinned image in mid-tier (e.g., 15m) | Earlier tiers play normally; when 15m tier starts, pinned image plays first within that tier. |
| Class mode, multiple pinned across different tiers | Each pinned image plays first within its own tier; tier order ascending preserved. |
| Class mode, multiple pinned in same tier | All play at the start of that tier, in pin order. |
| Empty image list | Returns `[]`. `_start_slideshow` early-returns on empty already. |
| Pinned image with timer not matching any configured tier (class mode) | Plays in its timer group — groups are derived from each image's `.timer`, not from `class_groups`. So a pinned 15m image plays in a 15m group even if the user's tiers are 30s/1m/5m. This matches today's behavior: tier assignment is not enforced by `_start_slideshow`, only by auto-distribute (which skips pinned). |

## Testing

**New file:** `tests/test_play_order.py`. Pure function, no Qt fixtures needed.

Required coverage:

1. `test_empty_list` — empty input returns empty output
2. `test_no_pinned_shuffle_off` — returns images in list order, identity
3. `test_no_pinned_shuffle_on` — returns same set (seeded random for determinism); verify all images present
4. `test_one_pinned_shuffle_off` — pinned first, rest in list order
5. `test_one_pinned_shuffle_on` — pinned first, rest shuffled
6. `test_multiple_pinned_preserve_pin_order` — pinned block in pin order, no shuffle within
7. `test_all_pinned` — pin order, no shuffle
8. `test_class_mode_tier_ascending` — without pinning, images sorted by timer ascending
9. `test_class_mode_pinned_first_within_tier` — pinned image in 15m tier plays first among 15m images; earlier tiers unchanged
10. `test_class_mode_multiple_pinned_across_tiers` — each tier's pinned come first in that tier
11. `test_class_mode_multiple_pinned_same_tier` — all pinned at start of that tier, pin order preserved

Random seeding: set `random.seed(N)` in tests that assert order under `shuffle=True`, or inject the RNG. Preference: accept non-determinism via `set` comparisons for "all images present" + use seeding for "pinned-first" assertions where order matters.

## Files touched

- `core/play_order.py` (new, ~30 lines)
- `ui/settings_window.py` (remove ~10 lines, add 2-line call)
- `tests/test_play_order.py` (new, ~80 lines)

Nothing else changes. `core/class_mode.py`, `core/models.py`, viewer, editor panel, and timer panel are all untouched.

## Risks

- **Non-deterministic shuffle in tests** — mitigated by seeded random or set-based assertions.
- **Saved session files** — `session.json` stores images with their `pinned` flag and timers; it does not store play order. No migration needed.
- **User relies on current pinned-last behavior** — unlikely but possible. Current behavior is buggy and undocumented; switching to pinned-first is the fix users asked for.

## Acceptance

- Unit tests for `build_play_order` pass
- Manual verification: pin one image in quick mode, start session with shuffle on → pinned image shown first
- Manual verification: pin one 15m image in class mode with 30s/1m/5m/15m tiers → 30s tier plays first, then 1m, then 5m, then pinned 15m image leads the 15m tier
- No regression in "no pinned images" sessions (behavior identical to today)
