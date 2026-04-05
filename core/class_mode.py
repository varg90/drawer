# core/class_mode.py
"""Class mode: distribute images into timed groups within a total session duration."""

from core.constants import CLASS_MODE_TEMPLATES


def auto_distribute(num_images, total_seconds, custom_tiers=None):
    """
    Distribute images into groups with increasing timer durations,
    fitting within total_seconds.

    custom_tiers: optional list of (seconds, label) to use instead of templates.

    Returns list of (count, timer_seconds) tuples.
    Example: [(5, 30), (4, 60), (3, 120), (2, 300)]
    """
    if num_images <= 0 or total_seconds <= 0:
        return []

    if custom_tiers and len(custom_tiers) > 0:
        tiers = sorted(custom_tiers, key=lambda t: t[0])
    elif total_seconds <= 900:
        tiers = CLASS_MODE_TEMPLATES["short"]
    elif total_seconds <= 3600:
        tiers = CLASS_MODE_TEMPLATES["medium"]
    else:
        tiers = CLASS_MODE_TEMPLATES["long"]

    num_tiers = len(tiers)

    # First pass: reserve 1 image per tier (if time allows)
    # This ensures all checked tiers are used
    min_time_needed = sum(t for t, _ in tiers)
    usable_tiers = []
    reserve_time = 0
    for tier_time, label in tiers:
        if reserve_time + tier_time <= total_seconds:
            usable_tiers.append((tier_time, label))
            reserve_time += tier_time

    if not usable_tiers:
        usable_tiers = [tiers[0]]

    # Can't use more tiers than images
    usable_tiers = usable_tiers[:num_images]

    num_tiers = len(usable_tiers)
    # Start with 1 image per tier
    groups = [(1, t) for t, _ in usable_tiers]
    used_images = num_tiers
    used_time = sum(t for t, _ in usable_tiers)

    # Second pass: distribute remaining images with weights (more short, fewer long)
    remaining_images = num_images - used_images
    remaining_time = total_seconds - used_time

    if remaining_images > 0 and remaining_time > 0:
        weights = list(range(num_tiers, 0, -1))
        total_weight = sum(weights)

        for i in range(num_tiers):
            if remaining_images <= 0 or remaining_time <= 0:
                break
            tier_time = usable_tiers[i][0]
            extra = round(remaining_images * weights[i] / total_weight)
            max_by_time = remaining_time // tier_time
            extra = min(extra, remaining_images, max_by_time)
            if extra > 0:
                old_count, t = groups[i]
                groups[i] = (old_count + extra, t)
                remaining_images -= extra
                remaining_time -= extra * tier_time

    # If images still remain, fill from last tier
    if remaining_images > 0:
        last_count, last_time = groups[-1]
        extra = min(remaining_images, remaining_time // last_time) if remaining_time > 0 else 0
        if extra > 0:
            groups[-1] = (last_count + extra, last_time)

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
    """Format a group for display: '5 × 30 сек'"""
    if timer_seconds >= 3600:
        t = f"{timer_seconds // 3600}ч {(timer_seconds % 3600) // 60}мин"
    elif timer_seconds >= 60:
        t = f"{timer_seconds // 60} мин"
    else:
        t = f"{timer_seconds} сек"
    return f"{count} × {t}"
