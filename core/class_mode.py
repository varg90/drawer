# core/class_mode.py
"""Class mode: distribute images into timed groups within a total session duration."""

from core.constants import CLASS_MODE_TEMPLATES


def auto_distribute(num_images, total_seconds):
    """
    Distribute images into groups with increasing timer durations,
    fitting within total_seconds.

    Returns list of (count, timer_seconds) tuples.
    Example: [(5, 30), (4, 60), (3, 120), (2, 300)]
    """
    if num_images <= 0 or total_seconds <= 0:
        return []

    # Pick template based on session length
    if total_seconds <= 900:       # up to 15 min
        tiers = CLASS_MODE_TEMPLATES["short"]
    elif total_seconds <= 3600:    # up to 1 hour
        tiers = CLASS_MODE_TEMPLATES["medium"]
    else:                          # over 1 hour
        tiers = CLASS_MODE_TEMPLATES["long"]

    # Distribute images across tiers with decreasing count
    # More images for short poses, fewer for long
    num_tiers = len(tiers)
    weights = list(range(num_tiers, 0, -1))  # e.g. [3, 2, 1] for 3 tiers
    total_weight = sum(weights)

    groups = []
    remaining_images = num_images
    remaining_time = total_seconds

    for i, (tier_time, _) in enumerate(tiers):
        if remaining_images <= 0 or remaining_time <= 0:
            break

        if i == num_tiers - 1:
            # Last tier gets all remaining images
            count = remaining_images
        else:
            count = max(1, round(num_images * weights[i] / total_weight))
            count = min(count, remaining_images)

        # Check if this group fits in remaining time
        group_time = count * tier_time
        if group_time > remaining_time:
            count = max(1, remaining_time // tier_time)
            if count == 0:
                break

        groups.append((count, tier_time))
        remaining_images -= count
        remaining_time -= count * tier_time

    # If images remain, add them to the last tier
    if remaining_images > 0 and groups:
        last_count, last_time = groups[-1]
        groups[-1] = (last_count + remaining_images, last_time)

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
