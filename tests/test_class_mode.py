import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.class_mode import auto_distribute, groups_to_timers, total_duration, format_group


def test_auto_distribute_basic():
    groups = auto_distribute(10, 600)  # 10 images, 10 min
    assert len(groups) > 0
    assert sum(c for c, _ in groups) <= 10
    assert sum(c for c, _ in groups) > 0


def test_auto_distribute_fits_time():
    groups = auto_distribute(10, 600)
    assert total_duration(groups) <= 600


def test_auto_distribute_long_session():
    groups = auto_distribute(20, 3600)  # 20 images, 1 hour
    assert sum(c for c, _ in groups) <= 20
    assert total_duration(groups) <= 3600


def test_auto_distribute_very_long():
    groups = auto_distribute(30, 10800)  # 30 images, 3 hours
    assert sum(c for c, _ in groups) <= 30
    assert total_duration(groups) <= 10800


def test_auto_distribute_plenty_of_time():
    # With enough time, all images should be used
    groups = auto_distribute(5, 3600)  # 5 images, 1 hour — plenty
    assert sum(c for c, _ in groups) == 5


def test_auto_distribute_single_image():
    groups = auto_distribute(1, 600)
    assert sum(c for c, _ in groups) == 1


def test_auto_distribute_zero():
    assert auto_distribute(0, 600) == []
    assert auto_distribute(10, 0) == []


def test_auto_distribute_increasing_timers():
    groups = auto_distribute(12, 1800)
    timers = [t for _, t in groups]
    # Timers should be non-decreasing (short to long)
    assert timers == sorted(timers)


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
    assert format_group(5, 30) == "5 × 30 сек"


def test_format_group_minutes():
    assert format_group(3, 120) == "3 × 2 мин"
    assert format_group(2, 300) == "2 × 5 мин"


def test_format_group_hours():
    assert format_group(1, 3600) == "1 × 1ч 0мин"
