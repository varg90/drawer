# Pinned-first Play Order Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make pinned images play first within each tier group in a Drawer session, fixing the current bug where pinned images play last (when shuffled) or get scattered by the class-mode timer sort.

**Architecture:** Extract play-order logic into a new pure function `build_play_order` in `core/play_order.py` (no Qt deps, unit-testable in isolation). Replace the ~10 lines of inline play-order logic in `ui/settings_window.py:_start_slideshow` with a single call to this function. Timer-assignment logic stays where it is; this plan only touches play order.

**Tech Stack:** Python 3.14, PyQt6 (untouched by this plan), pytest for tests, Python stdlib `random` and `itertools.groupby`.

**Spec:** `docs/superpowers/specs/2026-04-17-pinned-first-play-order-design.md`

---

## File Structure

- **Create:** `core/play_order.py` — pure function `build_play_order`. No Qt, no IO, no side effects (except `random.shuffle` when caller passes `shuffle=True`).
- **Create:** `tests/test_play_order.py` — unit tests. No Qt fixtures.
- **Modify:** `ui/settings_window.py` — replace 10 lines of inline play-order logic in `_start_slideshow` with a 2-line call. Add one import.

Rules enforced by the function:
1. Pinned images come before non-pinned within each tier group.
2. Pinned images preserve their pin order (input order of pinned==True items).
3. Non-pinned images shuffle (shuffle=True) or keep list order (shuffle=False).
4. In `mode="class"`, tier groups play ascending by `img.timer`. In `mode="quick"`, everything is one group.
5. Empty input → empty output.

---

### Task 1: Create `core/play_order.py` with empty + no-pinned identity behavior

**Files:**
- Create: `core/play_order.py`
- Test: `tests/test_play_order.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_play_order.py`:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.models import ImageItem
from core.play_order import build_play_order


def _img(path, timer=300, pinned=False):
    return ImageItem(path=path, timer=timer, pinned=pinned)


def test_empty_list_returns_empty():
    assert build_play_order([], shuffle=False, mode="quick") == []
    assert build_play_order([], shuffle=True, mode="quick") == []
    assert build_play_order([], shuffle=False, mode="class") == []


def test_quick_no_pinned_no_shuffle_is_identity():
    images = [_img("a.jpg"), _img("b.jpg"), _img("c.jpg")]
    result = build_play_order(images, shuffle=False, mode="quick")
    assert [i.path for i in result] == ["a.jpg", "b.jpg", "c.jpg"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_play_order.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.play_order'`

- [ ] **Step 3: Write minimal implementation**

Create `core/play_order.py`:

```python
"""Build play order for a Drawer session (pure function, no Qt).

Applies pinned-first ordering within tier groups. Quick mode treats all
images as one group; class mode groups by img.timer and plays groups
ascending (30s tier first, 1h tier last).
"""
import random
from itertools import groupby


def build_play_order(images, *, shuffle, mode):
    """Return the list of ImageItem in the order the viewer should show them.

    Rules:
    - Pinned images come first within each tier group, in pin order.
    - Non-pinned images follow; shuffled if shuffle=True, else list order.
    - mode="class": tier groups sorted ascending by img.timer.
    - mode="quick": all images in one group.
    """
    if not images:
        return []
    return list(images)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_play_order.py -v`
Expected: PASS for both tests.

- [ ] **Step 5: Commit**

```bash
git add core/play_order.py tests/test_play_order.py
git commit -m "feat: add build_play_order skeleton with identity behavior

New pure function in core/ for computing session play order.
Currently returns input unchanged — pinned-first and shuffle rules
arrive in subsequent commits.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Pinned-first in quick mode (no shuffle)

**Files:**
- Modify: `core/play_order.py`
- Test: `tests/test_play_order.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_play_order.py`:

```python
def test_quick_one_pinned_plays_first():
    images = [
        _img("a.jpg"),
        _img("b.jpg", pinned=True),
        _img("c.jpg"),
    ]
    result = build_play_order(images, shuffle=False, mode="quick")
    assert [i.path for i in result] == ["b.jpg", "a.jpg", "c.jpg"]


def test_quick_multiple_pinned_preserve_pin_order():
    images = [
        _img("a.jpg"),
        _img("b.jpg", pinned=True),
        _img("c.jpg"),
        _img("d.jpg", pinned=True),
    ]
    result = build_play_order(images, shuffle=False, mode="quick")
    # Pinned first (in their original relative order), then unpinned
    assert [i.path for i in result] == ["b.jpg", "d.jpg", "a.jpg", "c.jpg"]


def test_quick_all_pinned():
    images = [
        _img("x.jpg", pinned=True),
        _img("y.jpg", pinned=True),
    ]
    result = build_play_order(images, shuffle=False, mode="quick")
    assert [i.path for i in result] == ["x.jpg", "y.jpg"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_play_order.py -v`
Expected: FAIL on the three new tests (returned order is input order, not pinned-first).

- [ ] **Step 3: Implement pinned-first for quick mode**

Replace the body of `build_play_order` in `core/play_order.py`:

```python
import random
from itertools import groupby


def build_play_order(images, *, shuffle, mode):
    """Return the list of ImageItem in the order the viewer should show them.

    Rules:
    - Pinned images come first within each tier group, in pin order.
    - Non-pinned images follow; shuffled if shuffle=True, else list order.
    - mode="class": tier groups sorted ascending by img.timer.
    - mode="quick": all images in one group.
    """
    if not images:
        return []

    if mode == "class":
        return list(images)  # class-mode logic arrives in Task 4

    # Quick mode: one group
    pinned = [img for img in images if img.pinned]
    unpinned = [img for img in images if not img.pinned]
    return pinned + unpinned
```

- [ ] **Step 4: Run tests to verify all pass**

Run: `python -m pytest tests/test_play_order.py -v`
Expected: PASS on all five tests so far.

- [ ] **Step 5: Commit**

```bash
git add core/play_order.py tests/test_play_order.py
git commit -m "feat: pinned-first ordering for quick mode

Pinned images play first in pin order, non-pinned follow.
Shuffle and class mode still to come.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Shuffle non-pinned in quick mode

**Files:**
- Modify: `core/play_order.py`
- Test: `tests/test_play_order.py`

- [ ] **Step 1: Write the failing tests**

First, add `import random` to the imports at the top of `tests/test_play_order.py` (below the existing `sys, os` import). The file should now start:

```python
import sys, os
import random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.models import ImageItem
from core.play_order import build_play_order
```

Then append to `tests/test_play_order.py`:

```python
def test_quick_no_pinned_shuffle_preserves_set():
    random.seed(42)
    images = [_img(f"{c}.jpg") for c in "abcdefghij"]
    result = build_play_order(images, shuffle=True, mode="quick")
    # Same images, possibly different order
    assert set(i.path for i in result) == set(i.path for i in images)
    assert len(result) == len(images)


def test_quick_no_pinned_shuffle_actually_shuffles():
    """With 10 images and a fixed seed, shuffled order should differ from input."""
    random.seed(0)
    images = [_img(f"{c}.jpg") for c in "abcdefghij"]
    result = build_play_order(images, shuffle=True, mode="quick")
    assert [i.path for i in result] != [i.path for i in images]


def test_quick_pinned_first_rest_shuffled():
    random.seed(1)
    images = [
        _img("a.jpg"),
        _img("P.jpg", pinned=True),
        _img("b.jpg"),
        _img("c.jpg"),
        _img("d.jpg"),
    ]
    result = build_play_order(images, shuffle=True, mode="quick")
    # Pinned first, regardless of shuffle
    assert result[0].path == "P.jpg"
    # Remaining four are the non-pinned set
    assert set(i.path for i in result[1:]) == {"a.jpg", "b.jpg", "c.jpg", "d.jpg"}


def test_quick_multiple_pinned_not_shuffled_among_themselves():
    """Pinned images keep their pin order even when shuffle=True."""
    random.seed(2)
    images = [
        _img("a.jpg"),
        _img("P1.jpg", pinned=True),
        _img("b.jpg"),
        _img("P2.jpg", pinned=True),
        _img("c.jpg"),
    ]
    # Run several times to be confident order is deterministic for pinned
    for seed in range(5):
        random.seed(seed)
        result = build_play_order(images, shuffle=True, mode="quick")
        assert result[0].path == "P1.jpg"
        assert result[1].path == "P2.jpg"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_play_order.py -v`
Expected: `test_quick_no_pinned_shuffle_actually_shuffles` fails (current impl returns identity), and the pinned-shuffle tests may pass by accident — re-run after Step 3 anyway.

- [ ] **Step 3: Implement shuffle for non-pinned**

Update `build_play_order` in `core/play_order.py`:

```python
import random
from itertools import groupby


def build_play_order(images, *, shuffle, mode):
    """Return the list of ImageItem in the order the viewer should show them.

    Rules:
    - Pinned images come first within each tier group, in pin order.
    - Non-pinned images follow; shuffled if shuffle=True, else list order.
    - mode="class": tier groups sorted ascending by img.timer.
    - mode="quick": all images in one group.
    """
    if not images:
        return []

    if mode == "class":
        return list(images)  # class-mode logic arrives in Task 4

    # Quick mode: one group
    pinned = [img for img in images if img.pinned]
    unpinned = [img for img in images if not img.pinned]
    if shuffle:
        random.shuffle(unpinned)
    return pinned + unpinned
```

- [ ] **Step 4: Run tests to verify all pass**

Run: `python -m pytest tests/test_play_order.py -v`
Expected: PASS on all tests (9 so far).

- [ ] **Step 5: Commit**

```bash
git add core/play_order.py tests/test_play_order.py
git commit -m "feat: shuffle non-pinned in quick mode, preserve pinned order

Shuffle applies only to non-pinned images. Pinned remain first in
pin order across any seed.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Class mode — tier groups ascending, pinned-first within each tier

**Files:**
- Modify: `core/play_order.py`
- Test: `tests/test_play_order.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_play_order.py`:

```python
def test_class_no_pinned_tiers_ascending():
    images = [
        _img("a15m.jpg", timer=900),
        _img("a30s.jpg", timer=30),
        _img("b5m.jpg", timer=300),
        _img("b30s.jpg", timer=30),
    ]
    result = build_play_order(images, shuffle=False, mode="class")
    # 30s tier first, then 5m, then 15m
    assert [i.timer for i in result] == [30, 30, 300, 900]


def test_class_pinned_first_within_tier():
    """Pinned 15m image plays first within the 15m tier, not globally first."""
    images = [
        _img("s1.jpg", timer=30),
        _img("s2.jpg", timer=30),
        _img("m1.jpg", timer=300),
        _img("P15.jpg", timer=900, pinned=True),
        _img("m2.jpg", timer=300),
        _img("l1.jpg", timer=900),
    ]
    result = build_play_order(images, shuffle=False, mode="class")
    paths = [i.path for i in result]
    # Tiers ascending: 30s, then 5m, then 15m (pinned first in 15m)
    assert paths == ["s1.jpg", "s2.jpg", "m1.jpg", "m2.jpg", "P15.jpg", "l1.jpg"]


def test_class_multiple_pinned_across_different_tiers():
    images = [
        _img("s1.jpg", timer=30),
        _img("P30.jpg", timer=30, pinned=True),
        _img("m1.jpg", timer=300),
        _img("P5m.jpg", timer=300, pinned=True),
        _img("s2.jpg", timer=30),
    ]
    result = build_play_order(images, shuffle=False, mode="class")
    paths = [i.path for i in result]
    # 30s tier: P30 first, then s1, s2. 5m tier: P5m first, then m1.
    assert paths == ["P30.jpg", "s1.jpg", "s2.jpg", "P5m.jpg", "m1.jpg"]


def test_class_multiple_pinned_same_tier_preserve_order():
    images = [
        _img("a.jpg", timer=300),
        _img("P1.jpg", timer=300, pinned=True),
        _img("b.jpg", timer=300),
        _img("P2.jpg", timer=300, pinned=True),
    ]
    result = build_play_order(images, shuffle=False, mode="class")
    assert [i.path for i in result] == ["P1.jpg", "P2.jpg", "a.jpg", "b.jpg"]


def test_class_shuffle_only_shuffles_non_pinned_within_tier():
    random.seed(3)
    images = [
        _img("s1.jpg", timer=30),
        _img("s2.jpg", timer=30),
        _img("s3.jpg", timer=30),
        _img("PS.jpg", timer=30, pinned=True),
        _img("m1.jpg", timer=300),
    ]
    # Run across seeds to verify pinned deterministic, tier order stable
    for seed in range(5):
        random.seed(seed)
        result = build_play_order(images, shuffle=True, mode="class")
        timers = [i.timer for i in result]
        assert timers == [30, 30, 30, 30, 300]  # tier order stable
        assert result[0].path == "PS.jpg"       # pinned first in 30s tier
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_play_order.py -v`
Expected: the five new class-mode tests fail (current class branch returns `list(images)`).

- [ ] **Step 3: Implement class mode**

Update `build_play_order` in `core/play_order.py` — replace the entire function body:

```python
import random
from itertools import groupby


def build_play_order(images, *, shuffle, mode):
    """Return the list of ImageItem in the order the viewer should show them.

    Rules:
    - Pinned images come first within each tier group, in pin order.
    - Non-pinned images follow; shuffled if shuffle=True, else list order.
    - mode="class": tier groups sorted ascending by img.timer.
    - mode="quick": all images in one group.
    """
    if not images:
        return []

    if mode == "class":
        # Stable sort by timer — within a tier, original list order is preserved.
        sorted_by_timer = sorted(images, key=lambda i: i.timer)
        result = []
        for _timer, group_iter in groupby(sorted_by_timer, key=lambda i: i.timer):
            group = list(group_iter)
            pinned = [img for img in group if img.pinned]
            unpinned = [img for img in group if not img.pinned]
            if shuffle:
                random.shuffle(unpinned)
            result.extend(pinned + unpinned)
        return result

    # Quick mode: one group
    pinned = [img for img in images if img.pinned]
    unpinned = [img for img in images if not img.pinned]
    if shuffle:
        random.shuffle(unpinned)
    return pinned + unpinned
```

- [ ] **Step 4: Run tests to verify all pass**

Run: `python -m pytest tests/test_play_order.py -v`
Expected: PASS on all 14 tests.

Also run the full test suite to make sure nothing else broke:

Run: `python -m pytest -q`
Expected: all tests pass, no regressions.

- [ ] **Step 5: Commit**

```bash
git add core/play_order.py tests/test_play_order.py
git commit -m "feat: class mode pinned-first within tier groups

Tier groups play ascending by timer; within each tier, pinned images
come first in pin order, non-pinned follow (shuffled or natural).
build_play_order is now feature-complete.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Wire `build_play_order` into `_start_slideshow`

**Files:**
- Modify: `ui/settings_window.py` (lines 1-25 imports, lines 679-688 play-order block)

- [ ] **Step 1: Add the import**

In `ui/settings_window.py`, locate the import block around lines 12-16:

```python
from core.constants import SUPPORTED_FORMATS
from core.class_mode import groups_to_timers
from core.file_utils import filter_image_files, scan_folder, dedup_paths
from core.session import save_session, load_session
from core.models import ImageItem
```

Add `build_play_order` import after the class_mode import:

```python
from core.constants import SUPPORTED_FORMATS
from core.class_mode import groups_to_timers
from core.play_order import build_play_order
from core.file_utils import filter_image_files, scan_folder, dedup_paths
from core.session import save_session, load_session
from core.models import ImageItem
```

- [ ] **Step 2: Replace the inline play-order block**

In `ui/settings_window.py`, find `_start_slideshow` (starts at line 660). Locate this block at lines 679-688:

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

Replace those 10 lines with:

```python
        show_images = build_play_order(
            self.images, shuffle=self._shuffle, mode=mode,
        )
```

Leave everything before (timer-assignment block lines 666-677) and after (`settings = {...}` onward) untouched. The `random` import at line 3 stays — it's still used at line 442 for `random.choice`.

- [ ] **Step 3: Run unit tests**

Run: `python -m pytest -q`
Expected: all tests pass (including the 14 new play-order tests).

- [ ] **Step 4: Manual smoke test**

Launch the app:

Run: `python main.py`

Sanity check the three key scenarios. The app needs images — any folder with a few PNG/JPG files works. If the user has a saved session, load it.

**Scenario A — Quick mode, pinned first with shuffle:**
1. Switch to quick mode
2. Turn shuffle on (shuffle icon accent-colored)
3. Pin one image (context menu → Pin, or via editor)
4. Click play (or the start button)
5. Verify: the pinned image is the first image shown
6. Close the viewer

**Scenario B — Class mode, pinned within tier:**
1. Switch to class mode
2. Pin one image in a mid-timer tier (e.g., 5m)
3. Make sure the tier contains at least 2 other non-pinned images
4. Start session
5. Verify: 30s/1m tiers play first, then when the 5m tier starts, the pinned image is the first 5m image shown
6. Close the viewer

**Scenario C — No pinned images, regression check:**
1. Ensure no images are pinned
2. Start session in quick mode with shuffle on
3. Verify: images play in some random order, all shown, no errors
4. Start session in class mode
5. Verify: tiers play shortest-to-longest, as before
6. Close the viewer

If any scenario fails, do not commit. Diagnose (check `show_images` contents via a temporary `print` inside `_start_slideshow`), fix, re-run.

- [ ] **Step 5: Commit**

```bash
git add ui/settings_window.py
git commit -m "refactor: use build_play_order in _start_slideshow

Replaces 10 lines of inline play-order logic (pinned placed LAST when
shuffled, class-mode sort by timer) with a single call to the new
pure function. Fixes pinned-last shuffle bug; pinned images now lead
their tier group and survive class-mode ordering.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Self-review summary

- **Spec coverage:** Every rule from the spec (pinned-first within tier, pin order preserved, shuffle non-pinned, class tiers ascending, empty list, single group in quick) maps to at least one test in Tasks 1-4, and the call-site change in Task 5 covers the settings_window update described in the spec.
- **Placeholders:** none — every step has executable code or exact commands.
- **Type consistency:** function signature `build_play_order(images, *, shuffle, mode)` is identical across all tasks; tests import from `core.play_order` consistently.
- **Spec edge case — pinned image with timer not matching any configured tier:** covered implicitly by the class-mode implementation (grouping by `img.timer`, not by `class_groups`). Not tested explicitly; if the reviewer wants it, add a test mirroring `test_class_pinned_first_within_tier` with a pinned image whose timer doesn't appear on any other image. The existing tests already exercise mixed-timer scenarios.
- **Out of scope:** session-aware auto-distribute, pinned-aware auto-distribute, cross-tier drag-drop (specs #2, #3, #4 in the pinned-features roadmap).
