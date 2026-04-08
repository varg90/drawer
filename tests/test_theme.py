import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ui.theme import Theme


def test_dark_theme_has_required_keys():
    t = Theme("dark")
    assert t.bg == "#191919"
    assert t.text_primary == "#ddd"
    assert t.text_secondary == "#606060"


def test_light_theme_has_required_keys():
    t = Theme("light")
    assert t.bg == "#d4d4d4"
    assert t.text_primary == "#222"
    assert t.text_secondary == "#5a5a5a"


def test_default_is_dark():
    t = Theme()
    assert t.bg == "#191919"


def test_toggle():
    t = Theme("dark")
    t.toggle()
    assert t.bg == "#d4d4d4"
    t.toggle()
    assert t.bg == "#191919"


def test_name_property():
    t = Theme("dark")
    assert t.name == "dark"
    t.toggle()
    assert t.name == "light"


def test_accent_default():
    t = Theme("dark")
    assert t.accent == "#4a7d74"
    assert t.start_bg == "#4a7d74"


def test_accent_custom():
    t = Theme("dark", accent="#ff5500")
    assert t.accent == "#ff5500"
    assert t.start_bg == "#ff5500"
    assert t.border_active == "#ff5500"


def test_accent_setter():
    t = Theme("dark")
    t.accent = "#aa00bb"
    assert t.accent == "#aa00bb"
    assert t.start_bg == "#aa00bb"


def test_start_text_dark():
    t = Theme("dark")
    assert t.start_text == "#252525"


def test_start_text_light():
    t = Theme("light")
    assert t.start_text == "#c4c4c4"


def test_warning_color_dark():
    t = Theme("dark")
    assert t.warning == "#cc5555"


def test_warning_color_light():
    t = Theme("light")
    assert t.warning == "#cc4444"
