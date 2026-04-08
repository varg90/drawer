import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ui.widgets import make_icon_btn, make_start_btn, make_icon_toggle, make_centered_header, make_timer_btn


def test_make_icon_btn_returns_callable():
    assert callable(make_icon_btn)


def test_make_start_btn_returns_callable():
    assert callable(make_start_btn)


def test_make_icon_toggle_returns_callable():
    assert callable(make_icon_toggle)


def test_make_centered_header_returns_callable():
    assert callable(make_centered_header)


def test_make_timer_btn_returns_callable():
    assert callable(make_timer_btn)
