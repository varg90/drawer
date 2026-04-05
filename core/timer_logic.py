from core.constants import TIMER_MIN, TIMER_MAX

def validate_timer_seconds(seconds):
    return max(TIMER_MIN, min(TIMER_MAX, int(seconds)))

def format_time(s):
    if s >= 3600:
        return f"{s // 3600}:{(s % 3600) // 60:02d}:{s % 60:02d}"
    elif s >= 60:
        return f"{s // 60}:{s % 60:02d}"
    else:
        return f"0:{s:02d}"

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
