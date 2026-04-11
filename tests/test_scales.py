# tests/test_scales.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ui.scales import S


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
