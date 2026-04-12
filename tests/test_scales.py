# tests/test_scales.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ui.scales import S, sc, init_scale


def test_margins_defined():
    assert S.MARGIN == 14
    assert S.MARGIN_BOTTOM == 14


def test_icon_sizes():
    assert S.ICON_HEADER == 13
    assert S.ICON_START == 52


def test_start_button():
    assert S.START_ICON_RATIO == 0.75
    assert S.START_RADIUS_RATIO == 0.19


def test_font_sizes():
    assert S.FONT_TITLE == 17
    assert S.FONT_BUTTON == 11
    assert S.FONT_LABEL == 9


def test_window_sizes():
    assert S.MAIN_W == 250
    assert S.MAIN_H == 250
    assert S.EDITOR_W == 250
    assert S.WINDOW_RADIUS == 8


def test_new_radii():
    assert S.TIMER_BTN_RADIUS == 5
    assert S.MODE_BTN_RADIUS == 5
    assert S.PANEL_RADIUS == 6
    assert S.PANEL_PADDING == 6


def test_sc_default_factor():
    """At default factor 1.0, sc() returns the input unchanged."""
    assert sc(14) == 14
    assert sc(250) == 250
    assert sc(7) == 7


def test_sc_rounds_to_int():
    """sc() returns an integer."""
    assert isinstance(sc(14), int)


def test_init_scale_multiplies_values():
    """After init_scale(2.0), all S.* pixel constants are doubled."""
    init_scale(2.0)
    assert S.MAIN_W == 500
    assert S.MAIN_H == 500
    assert S.MARGIN == 28
    assert S.FONT_TITLE == 34
    assert S.ICON_START == 104
    # Ratios should NOT change
    assert S.START_ICON_RATIO == 0.75
    assert S.START_RADIUS_RATIO == 0.19
    # Reset to default
    init_scale(1.0)


def test_init_scale_reset():
    """init_scale(1.0) restores base values."""
    init_scale(2.0)
    init_scale(1.0)
    assert S.MAIN_W == 250
    assert S.MARGIN == 14
    assert S.FONT_TITLE == 17


def test_sc_uses_current_factor():
    """sc() reflects the most recent init_scale() call."""
    init_scale(1.5)
    assert sc(100) == 150
    assert sc(7) == 10  # round(7 * 1.5) = 10.5 -> 10
    init_scale(1.0)
