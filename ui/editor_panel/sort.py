# ui/editor_panel/sort.py
"""Group-tier sort helper."""


def _sort_group_items(items, pinned_first=True):
    """Sort items within a tier group.

    pinned_first=True: pinned images at the top of the group (quick mode).
    pinned_first=False: list order preserved, pin ignored (class mode).
    """
    if not pinned_first:
        return list(items)
    pinned = [i for i in items if getattr(i[1], "pinned", False)]
    unpinned = [i for i in items if not getattr(i[1], "pinned", False)]
    return pinned + unpinned
