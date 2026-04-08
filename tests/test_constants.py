import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.constants import SUPPORTED_FORMATS, TIMER_PRESETS, TIMER_MIN, TIMER_MAX

def test_supported_formats():
    assert ".jpg" in SUPPORTED_FORMATS
    assert ".txt" not in SUPPORTED_FORMATS

def test_timer_presets():
    assert len(TIMER_PRESETS) == 8
    assert [s for s, _ in TIMER_PRESETS] == [30, 60, 120, 300, 600, 900, 1800, 3600]

def test_timer_range():
    assert TIMER_MIN == 1
    assert TIMER_MAX == 10800

def test_timer_presets_has_2min():
    from core.constants import TIMER_PRESETS
    secs = [s for s, _ in TIMER_PRESETS]
    assert 120 in secs
