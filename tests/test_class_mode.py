import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.class_mode import auto_distribute, groups_to_timers, total_duration, format_group


def test_auto_distribute_basic():
    groups = auto_distribute(10, custom_tiers=[(30, "30s"), (60, "1m"), (300, "5m")])
    assert len(groups) > 0
    assert sum(c for c, _ in groups) == 10


def test_auto_distribute_single_image():
    groups = auto_distribute(1, custom_tiers=[(60, "1m"), (300, "5m")])
    assert sum(c for c, _ in groups) == 1


def test_auto_distribute_zero():
    assert auto_distribute(0) == []


def test_auto_distribute_increasing_timers():
    groups = auto_distribute(12, custom_tiers=[(30, "30s"), (60, "1m"), (300, "5m")])
    timers = [t for _, t in groups]
    assert timers == sorted(timers)


def test_auto_distribute_custom_tiers():
    tiers = [(60, "1m"), (300, "5m")]
    groups = auto_distribute(10, custom_tiers=tiers)
    for _, t in groups:
        assert t in (60, 300)


def test_auto_distribute_custom_single_tier():
    tiers = [(300, "5m")]
    groups = auto_distribute(5, custom_tiers=tiers)
    assert all(t == 300 for _, t in groups)


def test_auto_distribute_uses_all_tiers():
    tiers = [(60, "1m"), (300, "5m"), (600, "10m")]
    groups = auto_distribute(10, custom_tiers=tiers)
    used_timers = set(t for _, t in groups)
    assert used_timers == {60, 300, 600}


def test_auto_distribute_all_images_covered():
    """Every image gets a timer — no overflow."""
    tiers = [(30, "30s"), (60, "1m")]
    groups = auto_distribute(20, custom_tiers=tiers)
    assert sum(c for c, _ in groups) == 20


def test_auto_distribute_no_time_budget():
    """Without time budget, distribute all images across tiers."""
    groups = auto_distribute(10, custom_tiers=[(60, "1m"), (300, "5m")])
    assert sum(c for c, _ in groups) == 10
    used_timers = set(t for _, t in groups)
    assert used_timers == {60, 300}


def test_auto_distribute_single_tier_all_images():
    tiers = [(300, "5m")]
    groups = auto_distribute(8, custom_tiers=tiers)
    assert groups == [(8, 300)]


def test_groups_to_timers():
    groups = [(3, 30), (2, 60)]
    assert groups_to_timers(groups) == [30, 30, 30, 60, 60]


def test_groups_to_timers_empty():
    assert groups_to_timers([]) == []


def test_groups_to_timers_single():
    assert groups_to_timers([(1, 300)]) == [300]


def test_total_duration():
    groups = [(3, 30), (2, 60)]
    assert total_duration(groups) == 3 * 30 + 2 * 60  # 210


def test_total_duration_empty():
    assert total_duration([]) == 0


def test_format_group_seconds():
    assert format_group(5, 30) == "5 × 30s"


def test_format_group_minutes():
    assert format_group(3, 120) == "3 × 2m"
    assert format_group(2, 300) == "2 × 5m"


def test_format_group_hours():
    assert format_group(1, 3600) == "1 × 1h"


def test_auto_distribute_session_limit_none_matches_legacy():
    """With session_limit=None, auto_distribute must behave identically to
    the current (legacy) implementation. Regression safety for all existing
    callers that don't pass session_limit."""
    tiers = [(30, "30s"), (60, "1m"), (300, "5m")]
    result_none = auto_distribute(10, custom_tiers=tiers, session_limit=None)
    result_legacy = auto_distribute(10, custom_tiers=tiers)  # no kw at all
    assert result_none == result_legacy
    assert sum(c for c, _ in result_none) == 10
