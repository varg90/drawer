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


def test_session_limit_smaller_than_shortest_tier_returns_empty():
    """If budget can't fit even one image from the shortest tier, nothing is
    placed — all images overflow to Reserve."""
    tiers = [(30, "30s"), (300, "5m")]
    result = auto_distribute(10, custom_tiers=tiers, session_limit=10)
    assert result == []


def test_session_limit_zero_images_returns_empty():
    tiers = [(30, "30s"), (60, "1m")]
    result = auto_distribute(0, custom_tiers=tiers, session_limit=3600)
    assert result == []


def test_session_limit_one_round_fits_each_tier():
    """Session budget exactly fits one image per tier — should place exactly
    one per tier, no more."""
    tiers = [(30, "30s"), (60, "1m"), (300, "5m")]
    # Budget exactly fits one round: 30 + 60 + 300 = 390s
    result = auto_distribute(100, custom_tiers=tiers, session_limit=390)
    assert result == [(1, 30), (1, 60), (1, 300)]


def test_session_limit_1h_100imgs_four_tiers():
    """Worked example from spec: 1h session, 100 images, tiers
    [30s, 1m, 5m, 15m] → (8, 6, 4, 2) = 20 placed, 3600s exact."""
    tiers = [(30, "30s"), (60, "1m"), (300, "5m"), (900, "15m")]
    result = auto_distribute(100, custom_tiers=tiers, session_limit=3600)
    assert result == [(8, 30), (6, 60), (4, 300), (2, 900)]
    assert sum(c * t for c, t in result) == 3600


def test_session_limit_30m_50imgs_three_tiers():
    """Worked example: 30m, 50 images, tiers [30s, 5m, 15m] → (10, 2, 1)."""
    tiers = [(30, "30s"), (300, "5m"), (900, "15m")]
    result = auto_distribute(50, custom_tiers=tiers, session_limit=1800)
    assert result == [(10, 30), (2, 300), (1, 900)]
    assert sum(c * t for c, t in result) == 1800


def test_session_limit_2h_50imgs_four_tiers():
    """Worked example: 2h, 50 images, tiers [30s, 5m, 15m, 30m] →
    (10, 5, 2, 2) = 19 placed, 7200s exact."""
    tiers = [(30, "30s"), (300, "5m"), (900, "15m"), (1800, "30m")]
    result = auto_distribute(50, custom_tiers=tiers, session_limit=7200)
    assert result == [(10, 30), (5, 300), (2, 900), (2, 1800)]
    assert sum(c * t for c, t in result) == 7200


def test_session_limit_fewer_images_than_tiers_places_shortest_first():
    """2 images, 4 tiers selected, plenty of budget. Algorithm should place
    one image each in the two shortest tiers and stop (out of images)."""
    tiers = [(30, "30s"), (60, "1m"), (300, "5m"), (900, "15m")]
    result = auto_distribute(2, custom_tiers=tiers, session_limit=3600)
    assert result == [(1, 30), (1, 60)]


def test_session_limit_images_run_out_before_budget():
    """5 images, one tier, session much larger than needed. Placement stops
    at 5, not at budget."""
    tiers = [(30, "30s")]
    result = auto_distribute(5, custom_tiers=tiers, session_limit=3600)
    assert result == [(5, 30)]


def test_session_limit_invariant_total_duration_never_exceeds_budget():
    """Stress test: randomized inputs, assert total_duration(result) <=
    session_limit always. The invariant the algorithm must uphold."""
    import random as _rand
    _rand.seed(0)
    all_tiers = [(30, "30s"), (60, "1m"), (120, "2m"), (300, "5m"),
                 (600, "10m"), (900, "15m"), (1800, "30m"), (3600, "1h")]
    for _ in range(200):
        k = _rand.randint(1, len(all_tiers))
        tiers = _rand.sample(all_tiers, k)
        num_images = _rand.randint(1, 500)
        session_limit = _rand.randint(10, 14400)
        result = auto_distribute(
            num_images, custom_tiers=tiers, session_limit=session_limit)
        assert total_duration(result) <= session_limit
        assert sum(c for c, _ in result) <= num_images
