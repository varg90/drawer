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
