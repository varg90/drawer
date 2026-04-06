import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ui.theme import Theme


def test_dark_theme_has_required_keys():
    t = Theme("dark")
    assert t.bg == "#1c1c1c"
    assert t.text_primary == "#ccc"
    assert t.text_secondary == "#555"


def test_light_theme_has_required_keys():
    t = Theme("light")
    assert t.bg == "#d0d0d0"
    assert t.text_primary == "#2a2a2a"
    assert t.text_secondary == "#666"


def test_default_is_dark():
    t = Theme()
    assert t.bg == "#1c1c1c"


def test_toggle():
    t = Theme("dark")
    t.toggle()
    assert t.bg == "#d0d0d0"
    t.toggle()
    assert t.bg == "#1c1c1c"


def test_name_property():
    t = Theme("dark")
    assert t.name == "dark"
    t.toggle()
    assert t.name == "light"
