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


from main import detect_scale_factor


def test_detect_scale_factor_reference():
    """1080p screen returns factor 1.0."""
    assert detect_scale_factor(1080) == 1.0


def test_detect_scale_factor_qhd():
    """1440p screen returns factor ~1.33."""
    assert detect_scale_factor(1440) == round(1440 / 1080, 2)


def test_detect_scale_factor_4k():
    """2160p screen returns factor 2.0."""
    assert detect_scale_factor(2160) == 2.0


def test_detect_scale_factor_clamp_low():
    """Small screens clamp to 1.0."""
    assert detect_scale_factor(768) == 1.0


def test_detect_scale_factor_clamp_high():
    """Very large screens clamp to 2.0."""
    assert detect_scale_factor(4320) == 2.0


def test_all_base_values_recorded():
    """Every int attribute in S should be in _BASE."""
    from ui.scales import _BASE
    for attr in dir(S):
        if attr.startswith('_'):
            continue
        val = getattr(S, attr)
        if isinstance(val, int):
            assert attr in _BASE, f"S.{attr} not in _BASE dict"


def test_ratios_not_scaled():
    """Float ratios must not change after init_scale."""
    init_scale(2.0)
    assert S.START_ICON_RATIO == 0.75
    assert S.START_RADIUS_RATIO == 0.19
    init_scale(1.0)


def test_round_trip_all_constants():
    """init_scale(2.0) then init_scale(1.0) restores every constant."""
    from ui.scales import _BASE
    init_scale(2.0)
    init_scale(1.0)
    for attr, base_val in _BASE.items():
        actual = getattr(S, attr)
        assert actual == base_val, f"S.{attr}: expected {base_val}, got {actual}"


def test_init_scale_combined_factors():
    """init_scale accepts dpi_factor and user_factor separately."""
    init_scale(2.0, user_factor=1.2)
    # effective = 2.0 * 1.2 = 2.4
    assert S.MAIN_W == round(250 * 2.4)  # 600
    assert S.MARGIN == round(14 * 2.4)   # 34
    init_scale(1.0)


def test_init_scale_user_factor_only():
    """User factor alone works via rescale_user."""
    init_scale(1.0)
    from ui.scales import rescale_user
    rescale_user(1.5)
    assert S.MAIN_W == round(250 * 1.5)  # 375
    assert S.MARGIN == round(14 * 1.5)   # 21
    rescale_user(1.0)


def test_user_factor_from_saved_size():
    """Saved window size 300 with base 250 gives user_factor 1.2."""
    init_scale(1.0, user_factor=300 / 250)
    assert S.MAIN_W == round(250 * 1.2)  # 300
    init_scale(1.0)
