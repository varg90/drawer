from core.constants import TIMER_MIN, TIMER_MAX

def validate_timer_seconds(seconds):
    return max(TIMER_MIN, min(TIMER_MAX, int(seconds)))

def format_time(s):
    s = max(0, int(s))
    if s >= 3600:
        return f"{s // 3600}:{(s % 3600) // 60:02d}:{s % 60:02d}"
    elif s >= 60:
        return f"{s // 60}:{s % 60:02d}"
    else:
        return f"0:{s:02d}"

def short_label(seconds):
    """Convert seconds to compact label: 30→'30s', 60→'1m', 3600→'1h'."""
    if seconds >= 3600 and seconds % 3600 == 0:
        return f"{seconds // 3600}h"
    if seconds >= 60 and seconds % 60 == 0:
        return f"{seconds // 60}m"
    return f"{seconds}s"

def auto_warn_seconds(timer_seconds):
    if timer_seconds <= 120:
        return 10
    elif timer_seconds <= 300:
        return 30
    elif timer_seconds <= 900:
        return 60
    elif timer_seconds <= 3600:
        return 300
    else:
        return 600
