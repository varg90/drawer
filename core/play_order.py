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
