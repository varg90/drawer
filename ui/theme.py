"""Theme colors for dark and light modes."""


_DARK = {
    "bg": "#1c1c1c",
    "bg_secondary": "#1a1a1a",
    "bg_row_even": "#222",
    "bg_row_odd": "#282828",
    "bg_button": "#252525",
    "bg_active": "#333",
    "border": "#333",
    "border_active": "#444",
    "text_primary": "#ccc",
    "text_secondary": "#555",
    "text_hint": "#444",
    "text_header": "#777",
    "text_button": "#777",
    "start_bg": "#555",
    "start_text": "#eee",
}

_LIGHT = {
    "bg": "#d0d0d0",
    "bg_secondary": "#ddd",
    "bg_row_even": "#d8d8d8",
    "bg_row_odd": "#d2d2d2",
    "bg_button": "#c4c4c4",
    "bg_active": "#bbb",
    "border": "#aaa",
    "border_active": "#999",
    "text_primary": "#2a2a2a",
    "text_secondary": "#666",
    "text_hint": "#888",
    "text_header": "#555",
    "text_button": "#555",
    "start_bg": "#777",
    "start_text": "#eee",
}

_THEMES = {"dark": _DARK, "light": _LIGHT}


class Theme:
    def __init__(self, name="dark"):
        self._name = name if name in _THEMES else "dark"

    @property
    def name(self):
        return self._name

    def toggle(self):
        self._name = "light" if self._name == "dark" else "dark"

    def _colors(self):
        return _THEMES[self._name]

    def __getattr__(self, key):
        colors = _THEMES.get(self.__dict__.get("_name", "dark"), _DARK)
        if key in colors:
            return colors[key]
        raise AttributeError(f"Theme has no color '{key}'")
