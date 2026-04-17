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
    - mode="class": tier groups sorted ascending by img.timer. Caller must
      assign img.timer on every image before calling (settings_window's
      _start_slideshow does this immediately before the call).
    - mode="quick": all images in one group.
    """
    if mode not in ("quick", "class"):
        raise ValueError(f"unknown mode: {mode!r}")
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
