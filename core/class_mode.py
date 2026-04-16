# core/class_mode.py
"""Class mode: distribute images into timed groups across tiers."""

from core.constants import DEFAULT_TIERS


def auto_distribute(num_images, custom_tiers=None):
    """
    Distribute num_images across tiers evenly, short-to-long.
    All images are assigned — no overflow.

    custom_tiers: list of (seconds, label). Uses medium template if None.
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
