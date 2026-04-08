SUPPORTED_FORMATS = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp")

TIMER_PRESETS = [
    (30, "30s"),
    (60, "1m"),
    (120, "2m"),
    (300, "5m"),
    (600, "10m"),
    (900, "15m"),
    (1800, "30m"),
    (3600, "1h"),
]

TIMER_MIN = 1
TIMER_MAX = 10800

SESSION_PRESETS = [
    (300, "5 min"),
    (600, "10 min"),
    (900, "15 min"),
    (1800, "30 min"),
    (2700, "45 min"),
    (3600, "1 hr"),
    (5400, "1.5 hr"),
    (7200, "2 hr"),
    (10800, "3 hr"),
]

# Auto class-mode distributions: list of (timer_seconds, label) groups
# Pattern: warm-up short poses → medium → long
CLASS_MODE_TEMPLATES = {
    "short": [
        (30, "30 sec"),
        (60, "1 min"),
        (180, "3 min"),
    ],
    "medium": [
        (30, "30 sec"),
        (60, "1 min"),
        (180, "3 min"),
        (300, "5 min"),
        (600, "10 min"),
    ],
    "long": [
        (30, "30 sec"),
        (60, "1 min"),
        (180, "3 min"),
        (300, "5 min"),
        (600, "10 min"),
        (900, "15 min"),
        (1800, "30 min"),
        (3600, "1 hr"),
    ],
}
