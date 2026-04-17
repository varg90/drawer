# Session-aware auto_distribute Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `auto_distribute` respect the session limit so total distributed duration ≤ session budget. Overflow images go to the existing Reserve group (timer = 0). When session_limit is None, behavior is unchanged.

**Architecture:** Extend `core/class_mode.auto_distribute` with a `session_limit` parameter. Two branches: legacy (None) untouched, session-aware uses round-robin-with-skip. Call sites in `ui/settings_window.py` and `ui/timer_panel.py` forward the session limit. `BottomBar` emits `session_limit_changed` so the editor rebuilds live when the user clicks limit presets.

**Tech Stack:** Python 3.14, PyQt6, pytest. All algorithm work is pure Python (no Qt imports).

**Spec:** `docs/superpowers/specs/2026-04-17-session-aware-auto-distribute-design.md`

---

## File Structure

- **Modify:** `core/class_mode.py` — add `session_limit=None` param to `auto_distribute`. Keep legacy branch intact; add session-aware branch.
- **Modify:** `tests/test_class_mode.py` — add ~10 new tests covering the new branch; existing tests remain untouched to prove no regression.
- **Modify:** `ui/timer_panel.py` — forward `session_limit` to core.
- **Modify:** `ui/settings_window.py` — pass session_limit through, change overflow fallback from `timers[-1]` to `0`, filter Reserve images before `build_play_order`, wire new signal handler.
- **Modify:** `ui/bottom_bar.py` — add `session_limit_changed` pyqtSignal, emit from `_next_limit` and `_prev_limit`.

---

### Task 1: Add `session_limit=None` parameter to `auto_distribute` (backward compat)

**Files:**
- Modify: `core/class_mode.py`
- Test: `tests/test_class_mode.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_class_mode.py`:

```python
def test_auto_distribute_session_limit_none_matches_legacy():
    """With session_limit=None, auto_distribute must behave identically to
    the current (legacy) implementation. Regression safety for all existing
    callers that don't pass session_limit."""
    tiers = [(30, "30s"), (60, "1m"), (300, "5m")]
    result_none = auto_distribute(10, custom_tiers=tiers, session_limit=None)
    result_legacy = auto_distribute(10, custom_tiers=tiers)  # no kw at all
    assert result_none == result_legacy
    assert sum(c for c, _ in result_none) == 10
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_class_mode.py::test_auto_distribute_session_limit_none_matches_legacy -v`
Expected: FAIL with `TypeError: auto_distribute() got an unexpected keyword argument 'session_limit'`

- [ ] **Step 3: Add the parameter — pass-through only**

In `core/class_mode.py`, change the signature of `auto_distribute`:

```python
def auto_distribute(num_images, custom_tiers=None, session_limit=None):
    """
    Distribute num_images across tiers evenly, short-to-long.
    All images are assigned — no overflow.

    custom_tiers: list of (seconds, label). Uses medium template if None.
    session_limit: session duration budget in seconds, or None for unlimited.
        When set, returned groups' total duration will not exceed this.
    Returns list of (count, timer_seconds) tuples.
    """
    if num_images <= 0:
        return []

    if custom_tiers and len(custom_tiers) > 0:
        tiers = sorted(custom_tiers, key=lambda t: t[0])
    else:
        tiers = DEFAULT_TIERS

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

Note: the body is the existing implementation. Only the signature and docstring changed. The `session_limit` parameter is accepted but not yet used — that's Task 2.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_class_mode.py -v`
Expected: PASS on all existing tests AND the new `test_auto_distribute_session_limit_none_matches_legacy`.

- [ ] **Step 5: Commit**

```bash
git add core/class_mode.py tests/test_class_mode.py
git commit -m "feat: add session_limit param to auto_distribute (accept only)

Signature change, no behavior change. Session_limit is accepted but
not yet consumed — the session-aware algorithm lands in the next
commit. Existing tests all pass; added an explicit regression test
that session_limit=None matches the legacy call shape.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Implement session-aware round-robin-with-skip

**Files:**
- Modify: `core/class_mode.py`
- Test: `tests/test_class_mode.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_class_mode.py`:

```python
def test_session_limit_smaller_than_shortest_tier_returns_empty():
    """If budget can't fit even one image from the shortest tier, nothing is
    placed — all images overflow to Reserve."""
    tiers = [(30, "30s"), (300, "5m")]
    result = auto_distribute(10, custom_tiers=tiers, session_limit=10)
    assert result == []


def test_session_limit_zero_images_returns_empty():
    tiers = [(30, "30s"), (60, "1m")]
    result = auto_distribute(0, custom_tiers=tiers, session_limit=3600)
    assert result == []


def test_session_limit_one_round_fits_each_tier():
    """Session budget exactly fits one image per tier — should place exactly
    one per tier, no more."""
    tiers = [(30, "30s"), (60, "1m"), (300, "5m")]
    # Budget exactly fits one round: 30 + 60 + 300 = 390s
    result = auto_distribute(100, custom_tiers=tiers, session_limit=390)
    assert result == [(1, 30), (1, 60), (1, 300)]


def test_session_limit_1h_100imgs_four_tiers():
    """Worked example from spec: 1h session, 100 images, tiers
    [30s, 1m, 5m, 15m] → (8, 6, 4, 2) = 20 placed, 3600s exact."""
    tiers = [(30, "30s"), (60, "1m"), (300, "5m"), (900, "15m")]
    result = auto_distribute(100, custom_tiers=tiers, session_limit=3600)
    assert result == [(8, 30), (6, 60), (4, 300), (2, 900)]
    assert sum(c * t for c, t in result) == 3600


def test_session_limit_30m_50imgs_three_tiers():
    """Worked example: 30m, 50 images, tiers [30s, 5m, 15m] → (10, 2, 1)."""
    tiers = [(30, "30s"), (300, "5m"), (900, "15m")]
    result = auto_distribute(50, custom_tiers=tiers, session_limit=1800)
    assert result == [(10, 30), (2, 300), (1, 900)]
    assert sum(c * t for c, t in result) == 1800


def test_session_limit_2h_50imgs_four_tiers():
    """Worked example: 2h, 50 images, tiers [30s, 5m, 15m, 30m] →
    (10, 5, 2, 2) = 19 placed, 7200s exact."""
    tiers = [(30, "30s"), (300, "5m"), (900, "15m"), (1800, "30m")]
    result = auto_distribute(50, custom_tiers=tiers, session_limit=7200)
    assert result == [(10, 30), (5, 300), (2, 900), (2, 1800)]
    assert sum(c * t for c, t in result) == 7200


def test_session_limit_fewer_images_than_tiers_places_shortest_first():
    """2 images, 4 tiers selected, plenty of budget. Algorithm should place
    one image each in the two shortest tiers and stop (out of images)."""
    tiers = [(30, "30s"), (60, "1m"), (300, "5m"), (900, "15m")]
    result = auto_distribute(2, custom_tiers=tiers, session_limit=3600)
    assert result == [(1, 30), (1, 60)]


def test_session_limit_images_run_out_before_budget():
    """5 images, one tier, session much larger than needed. Placement stops
    at 5, not at budget."""
    tiers = [(30, "30s")]
    result = auto_distribute(5, custom_tiers=tiers, session_limit=3600)
    assert result == [(5, 30)]


def test_session_limit_invariant_total_duration_never_exceeds_budget():
    """Stress test: randomized inputs, assert total_duration(result) <=
    session_limit always. The invariant the algorithm must uphold."""
    import random as _rand
    _rand.seed(0)
    all_tiers = [(30, "30s"), (60, "1m"), (120, "2m"), (300, "5m"),
                 (600, "10m"), (900, "15m"), (1800, "30m"), (3600, "1h")]
    for _ in range(200):
        k = _rand.randint(1, len(all_tiers))
        tiers = _rand.sample(all_tiers, k)
        num_images = _rand.randint(1, 500)
        session_limit = _rand.randint(10, 14400)
        result = auto_distribute(
            num_images, custom_tiers=tiers, session_limit=session_limit)
        assert total_duration(result) <= session_limit
        assert sum(c for c, _ in result) <= num_images
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_class_mode.py -v -k session_limit`
Expected: FAIL on all new session_limit tests (algorithm not yet implemented; current body ignores session_limit and returns the legacy distribution).

- [ ] **Step 3: Implement the session-aware branch**

Replace the body of `auto_distribute` in `core/class_mode.py`:

```python
def auto_distribute(num_images, custom_tiers=None, session_limit=None):
    """
    Distribute num_images across tiers short-to-long.

    custom_tiers: list of (seconds, label). Uses medium template if None.
    session_limit: session duration budget in seconds, or None for unlimited.
        When set, returned groups' total duration will not exceed this;
        images that don't fit are omitted (caller places them in Reserve).
    Returns list of (count, timer_seconds) tuples.
    """
    if num_images <= 0:
        return []

    if custom_tiers and len(custom_tiers) > 0:
        tiers = sorted(custom_tiers, key=lambda t: t[0])
    else:
        tiers = DEFAULT_TIERS

    if session_limit is None:
        # Legacy: each tier gets at least one image, then round-robin the rest.
        num_tiers = len(tiers)
        usable_tiers = tiers[:num_images]
        num_tiers = len(usable_tiers)
        groups = [(1, t) for t, _ in usable_tiers]
        remaining = num_images - num_tiers

        while remaining > 0:
            for i in range(num_tiers):
                if remaining <= 0:
                    break
                old_count, t = groups[i]
                groups[i] = (old_count + 1, t)
                remaining -= 1

        return groups

    # Session-aware: round-robin shortest-first, skip any tier whose next
    # image wouldn't fit the remaining budget. Stop when no tier fits.
    counts = [0] * len(tiers)
    remaining_images = num_images
    remaining_budget = session_limit

    while True:
        added_this_round = False
        for i, (timer, _label) in enumerate(tiers):
            if remaining_images == 0:
                break
            if timer > remaining_budget:
                continue
            counts[i] += 1
            remaining_budget -= timer
            remaining_images -= 1
            added_this_round = True
        if not added_this_round:
            break

    return [(c, t) for c, (t, _) in zip(counts, tiers) if c > 0]
```

- [ ] **Step 4: Run tests to verify all pass**

Run: `python -m pytest tests/test_class_mode.py -v`
Expected: PASS on all tests (existing + 9 new session_limit tests).

Also run the full suite to be sure no cross-file regression:

Run: `python -m pytest -q`
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add core/class_mode.py tests/test_class_mode.py
git commit -m "feat: session-aware auto_distribute via round-robin with skip

When session_limit is provided, auto_distribute walks tiers
shortest-first adding one image per round, skipping any tier whose
next image would exceed the remaining budget. Stops when no tier
can accept another image. Overflow (num_images - placed) is the
caller's responsibility — expected to go to Reserve (timer=0).

Worked examples covered as explicit tests:
  1h / 100imgs / [30s,1m,5m,15m] → (8, 6, 4, 2)
  30m / 50imgs / [30s,5m,15m]    → (10, 2, 1)
  2h / 50imgs / [30s,5m,15m,30m] → (10, 5, 2, 2)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Forward session_limit through `TimerPanel.auto_distribute`

**Files:**
- Modify: `ui/timer_panel.py`

- [ ] **Step 1: Update the method signature and call**

In `ui/timer_panel.py`, replace the existing `auto_distribute` method (around lines 188–194):

```python
    def auto_distribute(self, image_count, session_limit=None):
        """Run auto-distribute for class mode. Returns groups list."""
        if not image_count:
            self._class_groups = []
            return
        self._class_groups = auto_distribute(
            image_count, custom_tiers=self.get_selected_tiers(),
            session_limit=session_limit)
```

- [ ] **Step 2: Sanity check — imports still work**

Run: `python -c "from ui.timer_panel import TimerPanel; print('OK')"`
Expected: prints `OK`.

- [ ] **Step 3: Run full test suite**

Run: `python -m pytest -q`
Expected: all tests pass (no test for timer_panel directly, but the import-level check ensures no syntax/signature issues).

- [ ] **Step 4: Commit**

```bash
git add ui/timer_panel.py
git commit -m "feat: TimerPanel.auto_distribute forwards session_limit

Optional session_limit param. Default None preserves every caller
that doesn't pass it. Call-site update (settings_window) in the
next commit.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Update `settings_window` — pass session_limit, Reserve fallback, filter Reserve at session start

**Files:**
- Modify: `ui/settings_window.py`

This task does four things in one file. They are coupled (any one alone would leave the code in a half-broken state), so they land together.

- [ ] **Step 1: `_reapply_timers` passes session_limit**

In `ui/settings_window.py`, replace `_reapply_timers` (around lines 205–212):

```python
    def _reapply_timers(self):
        """Re-run current mode's timer assignment on self.images. Call
        after any image-list change so newly added files land in the
        right tier in class mode instead of sitting at the add-time
        default."""
        if self._timer_panel.timer_mode == "class" and self.images:
            self._timer_panel.auto_distribute(
                len(self.images),
                session_limit=self._bottom_bar.get_session_limit(),
            )
            self._apply_class_timers()
```

- [ ] **Step 2: `_apply_class_timers` — fix indexing + Reserve fallback**

In `ui/settings_window.py`, locate `_apply_class_timers` (around lines 196–203). Today it uses `enumerate(self.images)` as its index, which means pinned images consume positional timer slots (non-pinned image at self.images index 5 gets `timers[5]` even if 3 images before it were pinned and skipped). This is inconsistent with `_start_slideshow`'s timer block, which uses an `idx` counter that only advances for non-pinned images.

With session-aware distribution, `len(timers)` becomes smaller than `num_non_pinned` and the `else` fallback starts firing for real — so the indexing mismatch becomes visible.

Replace the entire method with:

```python
    def _apply_class_timers(self):
        groups = self._timer_panel.class_groups
        if groups:
            timers = groups_to_timers(groups)
            idx = 0
            for img in self.images:
                if getattr(img, "pinned", False):
                    continue
                img.timer = timers[idx] if idx < len(timers) else 0
                idx += 1
```

Two changes: (1) `enumerate(self.images)` → `for img in self.images` with a separate `idx` that only advances on non-pinned, (2) `timers[-1]` → `0` on fallback.

This aligns `_apply_class_timers` with `_start_slideshow`'s convention. Pinned-vs-distribution interaction is still imperfect (tracked for spec #3) but no longer inconsistent between the two code paths.

- [ ] **Step 3: `_start_slideshow` timer-assignment block — same Reserve fallback**

In `ui/settings_window.py`, find the class-mode block inside `_start_slideshow` (around lines 671–677):

```python
        elif self._timer_panel.class_groups:
            timers = groups_to_timers(self._timer_panel.class_groups)
            idx = 0
            for img in self.images:
                if not img.pinned and idx < len(timers):
                    img.timer = timers[idx]
                    idx += 1
```

Replace with:

```python
        elif self._timer_panel.class_groups:
            timers = groups_to_timers(self._timer_panel.class_groups)
            idx = 0
            for img in self.images:
                if img.pinned:
                    continue
                img.timer = timers[idx] if idx < len(timers) else 0
                idx += 1
```

Note: the loop structure changes slightly — we now advance through every non-pinned image and assign either its tier timer or 0 (Reserve). The `idx += 1` moves outside the `if` so we don't stall when we run out of tier slots.

- [ ] **Step 4: `_start_slideshow` filters Reserve before `build_play_order`**

Still in `_start_slideshow`, locate the `build_play_order` call (added during spec #1, around lines 680–682):

```python
        show_images = build_play_order(
            self.images, shuffle=self._shuffle, mode=mode,
        )
```

Replace with:

```python
        playable = [img for img in self.images if img.timer > 0]
        if not playable:
            return  # all images overflowed to Reserve, nothing to play
        show_images = build_play_order(
            playable, shuffle=self._shuffle, mode=mode,
        )
```

- [ ] **Step 5: Sanity check — imports and syntax**

Run: `python -c "from ui.settings_window import SettingsWindow; print('OK')"`
Expected: prints `OK`.

- [ ] **Step 6: Run full test suite**

Run: `python -m pytest -q`
Expected: all tests pass (spec #1's `test_play_order` tests still green — they use positive timers; the change is only in the caller).

- [ ] **Step 7: Commit**

```bash
git add ui/settings_window.py
git commit -m "feat: wire session_limit through settings_window, Reserve on overflow

Four coupled changes, one commit:
1. _reapply_timers passes session_limit to TimerPanel
2. _apply_class_timers aligned to _start_slideshow's idx-based
   indexing (pinned images no longer consume positional timer slots)
3. Both _apply_class_timers and _start_slideshow's timer-assignment
   block fall back to 0 (Reserve) when there are more non-pinned
   images than tier slots — the prior timers[-1] fallback was a
   dead path with the old all-images-distributed algorithm and
   would dump overflow into the longest tier with the new
   session-aware one.
4. _start_slideshow filters timer==0 (Reserve) images before calling
   build_play_order so Reserve items are visible in the editor but
   don't play.

Early-return guard added when every image ends up in Reserve.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: BottomBar signal + live editor rebuild

**Files:**
- Modify: `ui/bottom_bar.py`
- Modify: `ui/settings_window.py`

- [ ] **Step 1: Add the signal and emit it**

In `ui/bottom_bar.py`, add a new signal declaration near the existing ones (around line 17–18):

Change from:
```python
    start_clicked = pyqtSignal()
    add_clicked = pyqtSignal()
```

To:
```python
    start_clicked = pyqtSignal()
    add_clicked = pyqtSignal()
    session_limit_changed = pyqtSignal()
```

Then, update `_next_limit` and `_prev_limit` (around lines 84–90) to emit the signal after updating the display:

```python
    def _next_limit(self):
        self._session_limit_index = (self._session_limit_index + 1) % len(SESSION_LIMIT_PRESETS)
        self._update_limit_display()
        self.session_limit_changed.emit()

    def _prev_limit(self, pos=None):
        self._session_limit_index = (self._session_limit_index - 1) % len(SESSION_LIMIT_PRESETS)
        self._update_limit_display()
        self.session_limit_changed.emit()
```

Do NOT emit from the `session_limit_index` setter (used during state restoration, where an explicit `_reapply_timers` will run after images load).

- [ ] **Step 2: Wire the signal in SettingsWindow**

In `ui/settings_window.py`, locate the signal-wiring block in `__init__` (around lines 157–158 where `start_clicked` and `add_clicked` are connected):

```python
        self._bottom_bar.start_clicked.connect(self._start_slideshow)
        self._bottom_bar.add_clicked.connect(self._open_editor)
```

Add a third connection:

```python
        self._bottom_bar.start_clicked.connect(self._start_slideshow)
        self._bottom_bar.add_clicked.connect(self._open_editor)
        self._bottom_bar.session_limit_changed.connect(self._on_session_limit_changed)
```

Then add the handler method. Place it near `_on_timer_config_changed` (around line 171) for locality:

```python
    def _on_session_limit_changed(self):
        """Session limit was clicked — rebuild distribution and summary."""
        self._reapply_timers()
        self._update_summary()
        if self._editor_visible:
            self.editor.refresh(self.images)
```

- [ ] **Step 3: Sanity check**

Run: `python -c "from ui.bottom_bar import BottomBar; from ui.settings_window import SettingsWindow; print('OK')"`
Expected: prints `OK`.

- [ ] **Step 4: Run full test suite**

Run: `python -m pytest -q`
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add ui/bottom_bar.py ui/settings_window.py
git commit -m "feat: live rebuild when session_limit changes

BottomBar emits session_limit_changed from _next_limit and
_prev_limit (user-initiated clicks only — state restoration goes
through a different path that re-runs timer assignment anyway).

SettingsWindow listens and reruns _reapply_timers, _update_summary,
and an editor refresh. User-visible: clicking the session-limit
button rebuilds tier counts in the editor and bottom-bar summary
in real time.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: Manual smoke test (for Oksana)

**Files:** none modified — user verification only.

This task is not executed by the implementer agent. Leave the instructions below in place so Oksana can run them after all code is merged.

- [ ] **Step 1: Launch app, set up test session**

Run: `python main.py`

Setup:
- Switch to class mode
- Select tiers: 30s, 1m, 5m, 15m
- Add at least 30 images (drag a folder in)
- Set session limit to "1h" in the bottom bar

Expected state: bottom-bar summary shows something like "20 × (mixed) · 1h". Editor shows four tier groups with approximate counts 8 × 30s, 6 × 1m, 4 × 5m, 2 × 15m. Remaining images appear in a greyed-out "Reserve" group at the bottom.

- [ ] **Step 2: Verify live rebuild on session-limit change**

Click the session-limit button (or right-click for previous preset). Each click should:
- Update the bottom-bar label
- Rebuild the editor tier groups with new counts
- Images move between tier groups and Reserve as the budget changes

Try: 1h → 30m → 1h → 2h → no limit. At "no limit", the Reserve group empties — every image gets assigned to a tier (legacy behavior).

- [ ] **Step 3: Verify tier selection change rebuilds**

Toggle tiers on and off in the timer panel. Each toggle should rebuild tier groups in the editor.

- [ ] **Step 4: Run a session and verify Reserve doesn't play**

Click start. The session should:
- Play only images with non-zero timers (those in 30s/1m/5m/15m tiers)
- Never show a Reserve image
- End when the session limit hits

If a pinned image is in a playing tier, it still plays first in that tier (spec #1 interaction intact).

- [ ] **Step 5: Report back**

If all four scenarios work, report "looks good." Otherwise, describe what didn't look right (screenshots welcome).

---

## Self-review summary

- **Spec coverage:** 
  - Signature change → Task 1
  - Session-aware algorithm → Task 2
  - Worked examples as tests → Task 2
  - Invariant test → Task 2
  - `TimerPanel` forwarding → Task 3
  - `_reapply_timers` passing limit → Task 4
  - Reserve fallback in `_apply_class_timers` → Task 4
  - Reserve fallback in `_start_slideshow` timer block → Task 4
  - Filter Reserve before `build_play_order` → Task 4
  - BottomBar signal + wiring → Task 5
  - Manual smoke → Task 6
- **No placeholders** — every step has executable code or exact commands.
- **Type consistency:** `auto_distribute(num_images, custom_tiers=None, session_limit=None)` is used consistently in tasks 1–3. The `Reserve` concept is always `img.timer == 0`. The `session_limit_changed` signal name matches across Task 5.
- **Out of scope:** pinned images consuming session budget (spec #3), pin visibility UX, cross-tier drag-drop (spec #4), the pre-existing positional tier-migration bug (also addressed in spec #3).
