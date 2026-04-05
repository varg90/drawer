from dataclasses import dataclass

@dataclass
class ImageItem:
    path: str
    timer: int = 300

    def to_dict(self):
        return {"path": self.path, "timer": self.timer}

    @classmethod
    def from_dict(cls, d):
        return cls(path=d["path"], timer=d.get("timer", 300))
