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
    "bg": "#f0f0f0",
    "bg_secondary": "#fff",
    "bg_row_even": "#fafafa",
    "bg_row_odd": "#f5f5f5",
    "bg_button": "#e8e8e8",
    "bg_active": "#ddd",
    "border": "#ccc",
    "border_active": "#ccc",
    "text_primary": "#222",
    "text_secondary": "#888",
    "text_hint": "#aaa",
    "text_header": "#666",
    "text_button": "#666",
    "start_bg": "#888",
    "start_text": "#fff",
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
