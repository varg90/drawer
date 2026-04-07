from dataclasses import dataclass

@dataclass
class ImageItem:
    path: str
    timer: int = 300
    source_url: str = ""

    def to_dict(self):
        d = {"path": self.path, "timer": self.timer}
        if self.source_url:
            d["source_url"] = self.source_url
        return d

    @classmethod
    def from_dict(cls, d):
        return cls(
            path=d["path"],
            timer=d.get("timer", 300),
            source_url=d.get("source_url", ""),
        )
