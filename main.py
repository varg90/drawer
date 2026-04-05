import customtkinter as ctk

SUPPORTED_FORMATS = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp")

TIMER_PRESETS = [
    (60, "1 мин"),
    (300, "5 мин"),
    (600, "10 мин"),
    (900, "15 мин"),
    (1800, "30 мин"),
    (3600, "1 час"),
]

TIMER_MIN = 1        # 1 second
TIMER_MAX = 10800    # 3 hours

if __name__ == "__main__":
    pass
