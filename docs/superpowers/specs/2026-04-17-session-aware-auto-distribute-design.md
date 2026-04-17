# Session-aware auto_distribute — Design

**Date:** 2026-04-17 (original), amended 2026-04-17 after manual smoke testing.
**Status:** Expanded scope after smoke-test findings (empty-distribution state + shuffle button overhaul). Not addressed: pinned-aware distribution (spec #3), cross-tier drag-drop (spec #4).
**Scope:** Make `auto_distribute` respect `session_limit`, overflow → Reserve, plus two expansions from smoke testing:
1. Fix the editor's behavior when the distribution is empty (budget too small to fit any tier)
2. Replace the shuffle *toggle* with an explicit shuffle *button* that visibly reorders the image list — unifying shuffle behavior across quick and class modes.

## Problem

`core/class_mode.auto_distribute(num_images, custom_tiers)` ignores session limit. It spreads every image round-robin across selected tiers, regardless of total duration. Consequences:

- 100 images × 1h session with tiers [30s, 1m, 5m, 15m] produces ~11 hours of content. Playback hits the session limit mid-run; ~60% of uploaded images never play, and the entire longest tier may be unreachable (the case Oksana hit during spec #1 testing).
- The editor displays tier counts that overpromise. Users see "25 × 15m" and plan accordingly; actual playback cuts off long before.
- Combined with the pre-existing positional tier-assignment (tracked separately as the tier-migration bug), the result feels non-deterministic.

## Goal

When `session_limit` is set, the distribution returned by `auto_distribute` must have total duration `≤ session_limit`. Images that don't fit are excluded from the distribution and, at the call-site layer, placed in the existing Reserve group (timer = 0). When `session_limit is None`, behavior is identical to today.

Secondary goal: editor updates live when the user changes session_limit in the bottom bar.

Explicitly **out of scope** (own specs):

- Pinned images influencing distribution budget (spec #3)
- Pin visibility / auto-pin-on-move UX (separate feedback)
- Cross-tier drag-and-drop (spec #4)
- Fixing the pre-existing positional tier-migration bug (its fix belongs with spec #3)

## Algorithm

Round-robin with skip, shortest-tier first.

Given `num_images`, `tiers` (sorted ascending by duration), `session_limit`:

1. If `num_images == 0` or `tiers` is empty → return `[]`.
2. If `session_limit is None` → existing behavior (current `auto_distribute`).
3. Else: initialize `groups = [(0, timer) for timer in tiers]` (counts start at 0). Track `remaining_budget = session_limit` and `remaining_images = num_images`.
4. Loop:
   - For each tier in order (shortest first):
     - If tier.timer > remaining_budget → skip this tier this round.
     - Else if remaining_images == 0 → stop entirely.
     - Else → groups[i].count += 1; remaining_budget -= tier.timer; remaining_images -= 1.
   - After the pass, if every tier was skipped (no additions made in this round) → stop.
5. Return groups, filtering out any with count == 0. (Existing behavior never produces count-0 tiers because it guarantees ≥1 per tier; the new session-limited branch can produce count-0 tiers when even the shortest round doesn't fit everything.)

Each tier naturally stops getting images when its duration exceeds the remaining budget, while shorter tiers keep accumulating. The result is self-balancing to the session size.

### Worked examples

**1h / 100 imgs / [30s, 1m, 5m, 15m]:**
- Round 1: (1,1,1,1) = 1290s, budget 2310
- Rounds 2: (2,2,2,2) = 2580s, budget 1020
- Round 3: add 30s (30), 1m (60), 5m (300), skip 15m (900 > 1020-30-60-300=630 after the earlier adds of this round; actually let's recompute: after 2,2,2,2 budget is 1020. Try 15m: 900 ≤ 1020 ✓ add → (2,2,2,3) budget 120. Next round: 30 ≤ 120 ✓ (3,2,2,3) budget 90, 60 ≤ 90 ✓ (3,3,2,3) budget 30, 300 skip, 15m skip. Next round: 30 ≤ 30 ✓ (4,3,2,3) budget 0, 60 skip, 300 skip, 900 skip. Next round: all skip → stop.)

Let me recompute cleanly — the algorithm walks tiers in order per round:

- Start (0,0,0,0), budget 3600.
- Round 1: +30→(1,0,0,0) b3570, +60→(1,1,0,0) b3510, +300→(1,1,1,0) b3210, +900→(1,1,1,1) b2310.
- Round 2: +30→b2280, +60→b2220, +300→b1920, +900→(2,2,2,2) b1020.
- Round 3: +30→b990, +60→b930, +300→b630, +900→(3,3,3,3) b−270. **No — 900 > 630 so skip.** (3,3,3,2) b630.
- Round 4: +30→b600, +60→b540, +300→b240, skip 900. (4,4,4,2) b240.
- Round 5: +30→b210, +60→b150, skip 300, skip 900. (5,5,4,2) b150.
- Round 6: +30→b120, +60→b60, skip, skip. (6,6,4,2) b60.
- Round 7: +30→b30, skip 60, skip 300, skip 900. (7,6,4,2) b30.
- Round 8: +30→b0, skip all others. (8,6,4,2) b0.
- Round 9: skip all → stop.
- **Result: (8 × 30s, 6 × 1m, 4 × 5m, 2 × 15m) = 20 placed, 3600s exact, 80 → Reserve.**

**30m / 50 imgs / [30s, 5m, 15m]:**
- (0,0,0) b1800.
- Round 1: 30→b1770, 300→b1470, 900→(1,1,1) b570.
- Round 2: 30→b540, 300→b240, skip 900. (2,2,1) b240.
- Round 3: 30→b210, skip 300, skip 900. (3,2,1) b210.
- Rounds 4–10: only 30s fits. Add 30 seven more times → (10,2,1) b0.
- **Result: (10 × 30s, 2 × 5m, 1 × 15m) = 13 placed, 37 → Reserve.**

**2h / 50 imgs / [30s, 5m, 15m, 30m]:**
- (0,0,0,0) b7200.
- Round 1: +30, +300, +900, +1800 → (1,1,1,1) b4170.
- Round 2: +30, +300, +900, +1800 → (2,2,2,2) b1140.
- Round 3: +30→b1110, +300→b810, skip 900 (810<900), skip 1800 → (3,3,2,2) b810.
- Round 4: +30→b780, +300→b480, skip, skip → (4,4,2,2) b480.
- Round 5: +30→b450, +300→b150, skip, skip → (5,5,2,2) b150.
- Round 6: +30→b120, skip 300, skip, skip → (6,5,2,2) b120.
- Rounds 7–10: only 30s. Add 4 more 30s → (10,5,2,2) b0.
- **Result: (10 × 30s, 5 × 5m, 2 × 15m, 2 × 30m) = 19 placed, 31 → Reserve.**

These three traces become explicit regression tests.

## Architecture

### Pure function change

**File:** `core/class_mode.py`

Signature evolves from:
```python
def auto_distribute(num_images, custom_tiers=None)
```
to:
```python
def auto_distribute(num_images, custom_tiers=None, session_limit=None)
```

When `session_limit is None`, the implementation must match the existing behavior byte-for-byte (regression safety). When `session_limit` is set, the algorithm above runs.

Invariant: `total_duration(result) <= session_limit` always holds when `session_limit` is set.

### Call-site changes

**File:** `ui/timer_panel.py` (`TimerPanel.auto_distribute` method)

Forwards a new `session_limit` argument to the core function. The method becomes:
```python
def auto_distribute(self, image_count, session_limit=None):
    if not image_count:
        self._class_groups = []
        return
    self._class_groups = auto_distribute(
        image_count, custom_tiers=self.get_selected_tiers(),
        session_limit=session_limit,
    )
```

**File:** `ui/settings_window.py` (two spots)

1. `_reapply_timers` now passes the current session limit:
```python
def _reapply_timers(self):
    if self._timer_panel.timer_mode == "class" and self.images:
        self._timer_panel.auto_distribute(
            len(self.images),
            session_limit=self._bottom_bar.get_session_limit(),
        )
        self._apply_class_timers()
```

2. `_apply_class_timers`: change the overflow fallback from `timers[-1]` to `0` (Reserve):
```python
img.timer = timers[i] if i < len(timers) else 0
```

3. `_start_slideshow` timer-assignment block: same fallback change (Reserve instead of longest-tier).

4. `_start_slideshow` before calling `build_play_order`: filter out Reserve images so they don't play:
```python
playable = [img for img in self.images if img.timer > 0]
show_images = build_play_order(playable, shuffle=self._shuffle, mode=mode)
```

### Signal wiring

**File:** `ui/bottom_bar.py`

Add a `session_limit_changed = pyqtSignal()` signal and emit it from the two places that mutate `_session_limit_index` (the up/down buttons or whatever controls exist). That's ~5 lines.

**File:** `ui/settings_window.py`

In the signal-wiring section (around line 157 alongside `start_clicked`/`add_clicked`), add:
```python
self._bottom_bar.session_limit_changed.connect(self._on_session_limit_changed)
```

New handler:
```python
def _on_session_limit_changed(self):
    self._reapply_timers()
    self._update_summary()
    if self._editor_visible:
        self.editor.refresh(self.images)
```

This makes the editor tier counts and the bottom-bar summary update live as the user clicks through session-limit presets.

## Edge cases

| Case | Behavior |
|------|----------|
| `session_limit=None` | Identical to today. Pure function returns same shape; call sites preserve old fallback path (`timers[-1]`) — see "Backward compatibility" below. |
| No images (`num_images == 0`) | Return `[]`. No distribution. |
| No tiers selected | Return `[]`. (UI shouldn't allow this but function defends.) |
| All tiers fit one round, budget left over | Keep round-robinning; shorter tiers will outlive longer ones. Natural stopping condition. |
| Budget < shortest tier | Return `[]`. Every image → Reserve. Viewer is launched with 0 playable images; `_start_slideshow`'s existing `if not self.images: return` doesn't cover this case — add an early-return when `playable == []`. |
| One tier, huge budget | Round-robin adds until images or budget runs out. Same as today for single-tier configs. |
| Pinned image with pre-set `.timer` | Out of scope — positional assignment still skips pinned. Pinned images keep whatever timer they had. Spec #3 will fix. |
| User changes session_limit mid-editing | `session_limit_changed` signal → editor rebuilds → counts update. |
| User drags image manually into a tier | Existing behavior — `img.timer` changed directly, image is pinned (pre-existing auto-pin-on-move). No interaction with this spec. |

### Backward compatibility

When `session_limit=None`, the new call sites pass `None` through and the old fallback path matters. Specifically, `_apply_class_timers` today uses `timers[-1]` when `i >= len(timers)`. Is that path reachable when `session_limit=None`?

Current `auto_distribute(num_images, tiers)` always produces `num_images` total slots (count-sum == num_images by construction). So `groups_to_timers` produces exactly `num_images` entries, meaning `i < len(timers)` always. The `timers[-1]` fallback is dead code today.

With `session_limit=None`, the new implementation preserves this — `timers[-1]` remains unreachable, no regression.

With `session_limit` set, the fallback becomes reachable (overflow exists). Switching it to `0` (Reserve) is the intended behavior, not a regression.

## Testing

### New tests in `tests/test_class_mode.py`

- `test_auto_distribute_no_session_limit_unchanged` — all existing tests still pass, proving no regression when `session_limit=None`.
- `test_session_limit_none_equals_legacy` — explicitly: calling new and old behavior with `session_limit=None` returns identical output for representative inputs.
- `test_session_limit_smaller_than_any_tier` — budget 10s, tiers [30s, 5m], returns `[]`.
- `test_session_limit_fits_one_round` — budget = sum of tier durations exactly, returns 1 per tier.
- `test_session_limit_budget_exact` — one of the worked examples above, verify exact counts.
- `test_session_limit_1h_100imgs_four_tiers` — (8, 6, 4, 2) expected.
- `test_session_limit_30m_50imgs_three_tiers` — (10, 2, 1) expected.
- `test_session_limit_2h_50imgs_four_tiers` — (10, 5, 2, 2) expected.
- `test_session_limit_zero_images` — `auto_distribute(0, ..., session_limit=3600) == []`.
- `test_session_limit_invariant_total_duration_under_budget` — randomized property test: `total_duration(result) <= session_limit` for many random inputs.

### Integration test (manual smoke)

1. Launch app, class mode, tiers 30s/1m/5m/15m, 50+ images, session limit 1h.
2. Verify bottom-bar summary and editor tier counts match (8, 6, 4, 2) ± rounding.
3. Click session-limit up/down; editor counts rebuild live.
4. Change tier selection; editor counts rebuild.
5. Start session; 15m pinned image (if any) plays first in 15m tier (spec #1 interaction still works).
6. Session runs out at session_limit; Reserve images never appeared.

## Risks

- **Live editor rebuilds on session_limit change** — first time the editor re-layouts on a bottom-bar click. Smoke test for flicker or lag on 200+ image folders.
- **Reserve group rendering** — timer=0 group must render in both list and grid editor views. The code already has `is_reserve` branches (we verified in exploration), but they were only exercised by the quirky `timers[-1]` fallback, so the code path is cold. Manual verification needed.
- **Bottom-bar signal plumbing** — `BottomBar.session_limit_changed` is a new signal on an existing widget. Low risk, but touches a file with other UI logic. Keep the change minimal.

## Expansion 1 — Empty-distribution state (found in smoke testing)

**Problem:** When `session_limit` is smaller than every selected tier (e.g., 1-minute limit, only 15m tier selected), `auto_distribute` correctly returns `[]`. But the downstream code mishandles this:

1. `_apply_class_timers` has `if groups:` at the top — when empty, the method silently returns, so images keep stale `.timer` values from a previous distribution. The editor shows a phantom tier populated by those stale timers.
2. `BottomBar.update_summary_class` hides the session-limit button entirely when `class_groups` is empty, so the user can't even see what limit caused the empty state.
3. Starting a session in this state plays the stale-timer images anyway.

**Fix:**

1. `_apply_class_timers` must always loop over non-pinned images. When `groups` is empty, every non-pinned gets `.timer = 0` (→ Reserve). Same change mirrored in `_start_slideshow`'s class-mode timer block.
2. `BottomBar.update_summary_class` keeps the limit button visible even when `class_groups` is empty (show the limit, even if distribution is empty). Total-duration label shows `0:00` or hides gracefully; limit button stays visible so user knows what's constraining them.

## Expansion 2 — Shuffle becomes a button, not a toggle

**Problem:** Spec #1 introduced a shuffle toggle that auto-randomizes play order at session start. In class mode, this means:
- Editor preview doesn't reflect what will actually play (shuffle happens at Start)
- There's no way for the user to reroll *which images* go into *which tiers* — only the order within a tier
- Reserve images stay in Reserve forever (same images every session)

Adding a separate "Reroll" action alongside the existing toggle creates two similar-but-subtly-different features, which is confusing.

**Fix: Convert shuffle from state-based to action-based.** The shuffle control is a button, not a toggle. Clicking it visibly reorders the non-pinned image list.

- **Quick mode**: Click shuffle → `self.images` (non-pinned) is shuffled in place → editor reflects the new order → next session plays in that order.
- **Class mode**: Click shuffle → `self.images` (non-pinned) is shuffled → `_reapply_timers` rebuilds distribution from the new order → editor shows the new distribution (different images in different tiers, different ones in Reserve) → next session plays exactly that.

**Consequences:**

- No persistent "shuffle mode" state. The image list IS the order; shuffle button is just the "reorder now" action.
- `build_play_order`'s `shuffle` parameter becomes redundant and is removed.
- `_shuffle` state variable is removed from `SettingsWindow` and `EditorPanel`.
- The `shuffle` field in session.json is no longer written (reading legacy saved files ignores it safely).
- The editor's shuffle icon stays (same visual affordance) but its click semantics change: no more "on/off highlighted" state — pressed state is momentary (like any action button).
- Behavioral change: sessions are no longer automatically randomized. User opts in to random variety by clicking shuffle. Deterministic is the default.

## Acceptance

- `auto_distribute(..., session_limit=None)` is byte-identical to today for all existing test inputs.
- `auto_distribute(..., session_limit=N)` returns groups with total duration ≤ N.
- Three worked examples above produce the exact documented counts.
- Live editor update on session-limit change works in manual smoke test.
- Empty-distribution smoke scenario: select a single long tier with a sub-tier budget (e.g., 15m tier + 1m limit). Editor shows all images in Reserve, limit button remains visible, Start does nothing (early-return).
- Shuffle button smoke scenario: click shuffle in class mode with Reserve populated. Editor visibly reorders images across tiers and Reserve. Start plays exactly what the preview showed.
- No regression in spec #1 tests (pinned-first ordering still works), though tests that assert `shuffle=True` behavior are removed — the parameter no longer exists.
