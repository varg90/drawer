"""Theme colors for dark and light modes with custom accent support."""


DEFAULT_ACCENT = "#4a7d74"

_DARK_BASE = {
    "bg": "#16120e",
    "bg_secondary": "#120e0a",
    "bg_row_even": "#1a1610",
    "bg_row_odd": "#1e1a14",
    "bg_button": "#16120e",
    "border": "#120e0a",
    "text_primary": "#ccc0ae",
    "text_secondary": "#7a6b5a",
    "text_hint": "#4a3e32",
    "start_text": "#16120e",
    "warning": "#cc5555",
}

_LIGHT_BASE = {
    "bg": "#d8ccb8",
    "bg_secondary": "#e0d6c4",
    "bg_row_even": "#d4c8b4",
    "bg_row_odd": "#d0c4ae",
    "bg_button": "#d8ccb8",
    "border": "#c0b4a0",
    "text_primary": "#2a2018",
    "text_secondary": "#5a5248",
    "text_hint": "#a0947e",
    "start_text": "#d8ccb8",
    "warning": "#cc4444",
}

_BASES = {"dark": _DARK_BASE, "light": _LIGHT_BASE}


def _hex_to_rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = h[0]*2 + h[1]*2 + h[2]*2
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgb_to_hex(r, g, b):
    return f"#{int(r):02x}{int(g):02x}{int(b):02x}"


def _mix(color_a, color_b, t=0.5):
    ra, ga, ba = _hex_to_rgb(color_a)
    rb, gb, bb = _hex_to_rgb(color_b)
    return _rgb_to_hex(
        ra + (rb - ra) * t,
        ga + (gb - ga) * t,
        ba + (bb - ba) * t,
    )


def _darken(color, amount=0.3):
    r, g, b = _hex_to_rgb(color)
    return _rgb_to_hex(r * (1 - amount), g * (1 - amount), b * (1 - amount))


def _lighten(color, amount=0.3):
    r, g, b = _hex_to_rgb(color)
    return _rgb_to_hex(
        r + (255 - r) * amount,
        g + (255 - g) * amount,
        b + (255 - b) * amount,
    )


def _accent_colors(accent, mode):
    """Derive accent-dependent colors from a single accent hex."""
    if mode == "dark":
        return {
            "bg_active": _mix("#1a1610", accent, 0.15),
            "bg_panel": "#120e0a",
            "border_active": accent,
            "text_header": "#6b5e4e",
            "text_button": _mix(accent, "#ccc0ae", 0.4),
            "start_bg": accent,
        }
    else:
        return {
            "bg_active": _lighten(accent, 0.65),
            "bg_panel": "#c8bca4",
            "border_active": accent,
            "text_header": "#7a6e5e",
            "text_button": _darken(accent, 0.15),
            "start_bg": accent,
        }


class Theme:
    def __init__(self, name="dark", accent=None):
        self._name = name if name in _BASES else "dark"
        self._accent = accent or DEFAULT_ACCENT
        self._cache = {}
        self._cache_key = None

    @property
    def name(self):
        return self._name

    @property
    def accent(self):
        return self._accent

    @accent.setter
    def accent(self, value):
        self._accent = value

    def toggle(self):
        self._name = "light" if self._name == "dark" else "dark"

    def _colors(self):
        key = (self._name, self._accent)
        if self._cache_key != key:
            base = dict(_BASES[self._name])
            base.update(_accent_colors(self._accent, self._name))
            # Ghost: barely-visible tint for easter-egg icons. 10% toward
            # text_hint — legible if you look for it, invisible at a glance.
            base["text_ghost"] = _mix(base["bg"], base["text_hint"], 0.1)
            for k in list(base):
                if not base[k]:
                    continue
                r, g, b = _hex_to_rgb(base[k])
                base[k + "_rgb"] = f"{r}, {g}, {b}"
            self._cache = base
            self._cache_key = key
        return self._cache

    def __getattr__(self, key):
        colors = self._colors()
        if key in colors:
            return colors[key]
        raise AttributeError(f"Theme has no color '{key}'")
