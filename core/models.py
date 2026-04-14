from dataclasses import dataclass

# Default per-image timer in seconds. Used as the add-time fallback
# before a mode-aware redistribute kicks in, and as the on-disk default
# when a saved session is missing a timer field.
DEFAULT_TIMER_SECONDS = 300

@dataclass
class ImageItem:
    path: str
    timer: int = DEFAULT_TIMER_SECONDS
    source_url: str = ""
    pinned: bool = False

    def to_dict(self):
        d = {"path": self.path, "timer": self.timer}
        if self.source_url:
            d["source_url"] = self.source_url
        if self.pinned:
            d["pinned"] = True
        return d

    @classmethod
    def from_dict(cls, d):
        return cls(
            path=d["path"],
            timer=d.get("timer", DEFAULT_TIMER_SECONDS),
            source_url=d.get("source_url", ""),
            pinned=d.get("pinned", False),
        )
