import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ui.theme import Theme


def test_dark_theme_has_required_keys():
    t = Theme("dark")
    assert t.bg == "#16120e"
    assert t.text_primary == "#ccc0ae"
    assert t.text_secondary == "#7a6b5a"


def test_light_theme_has_required_keys():
    t = Theme("light")
    assert t.bg == "#d8ccb8"
    assert t.text_primary == "#2a2018"
    assert t.text_secondary == "#5a5248"


def test_default_is_dark():
    t = Theme()
    assert t.bg == "#16120e"


def test_toggle():
    t = Theme("dark")
    t.toggle()
    assert t.bg == "#d8ccb8"
    t.toggle()
    assert t.bg == "#16120e"


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
    assert t.start_text == "#16120e"


def test_start_text_light():
    t = Theme("light")
    assert t.start_text == "#d8ccb8"


def test_warning_color_dark():
    t = Theme("dark")
    assert t.warning == "#cc5555"


def test_warning_color_light():
    t = Theme("light")
    assert t.warning == "#cc4444"


def test_bg_panel_dark():
    t = Theme("dark")
    assert t.bg_panel == "#120e0a"


def test_bg_panel_light():
    t = Theme("light")
    assert t.bg_panel == "#c8bca4"


def test_rgb_variants():
    t = Theme("dark")
    assert t.bg_rgb == "22, 18, 14"
    t2 = Theme("light")
    assert t2.bg_rgb == "216, 204, 184"


def test_all_base_attrs_accessible_dark():
    t = Theme("dark")
    for attr in ("bg", "bg_secondary", "bg_row_even", "bg_row_odd", "bg_button",
                 "border", "text_primary", "text_secondary", "text_hint",
                 "start_text", "warning", "bg_active", "bg_panel", "border_active",
                 "text_header", "text_button", "start_bg"):
        assert getattr(t, attr), f"Missing attr: {attr}"


def test_all_base_attrs_accessible_light():
    t = Theme("light")
    for attr in ("bg", "bg_secondary", "bg_row_even", "bg_row_odd", "bg_button",
                 "border", "text_primary", "text_secondary", "text_hint",
                 "start_text", "warning", "bg_active", "bg_panel", "border_active",
                 "text_header", "text_button", "start_bg"):
        assert getattr(t, attr), f"Missing attr: {attr}"
