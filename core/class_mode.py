# core/class_mode.py
"""Class mode: distribute images into timed groups across tiers."""

from core.constants import DEFAULT_TIERS


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


def groups_to_timers(groups):
    """
    Convert groups [(count, timer), ...] to flat list of timer values.
    Example: [(3, 30), (2, 60)] -> [30, 30, 30, 60, 60]
    """
    result = []
    for count, timer in groups:
        result.extend([timer] * count)
    return result


def total_duration(groups):
    """Calculate total duration of all groups in seconds."""
    return sum(count * timer for count, timer in groups)


def format_group(count, timer_seconds):
    """Format a group for display: '5 × 30s'"""
    from core.timer_logic import short_label
    return f"{count} \u00d7 {short_label(timer_seconds)}"
