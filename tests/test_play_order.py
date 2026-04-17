import sys, os
import random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.models import ImageItem
from core.play_order import build_play_order


def _img(path, timer=300, pinned=False):
    return ImageItem(path=path, timer=timer, pinned=pinned)


def test_empty_list_returns_empty():
    assert build_play_order([], shuffle=False, mode="quick") == []
    assert build_play_order([], shuffle=True, mode="quick") == []
    assert build_play_order([], shuffle=False, mode="class") == []


def test_quick_no_pinned_no_shuffle_is_identity():
    images = [_img("a.jpg"), _img("b.jpg"), _img("c.jpg")]
    result = build_play_order(images, shuffle=False, mode="quick")
    assert [i.path for i in result] == ["a.jpg", "b.jpg", "c.jpg"]


def test_quick_one_pinned_plays_first():
    images = [
        _img("a.jpg"),
        _img("b.jpg", pinned=True),
        _img("c.jpg"),
    ]
    result = build_play_order(images, shuffle=False, mode="quick")
    assert [i.path for i in result] == ["b.jpg", "a.jpg", "c.jpg"]


def test_quick_multiple_pinned_preserve_pin_order():
    images = [
        _img("a.jpg"),
        _img("b.jpg", pinned=True),
        _img("c.jpg"),
        _img("d.jpg", pinned=True),
    ]
    result = build_play_order(images, shuffle=False, mode="quick")
    # Pinned first (in their original relative order), then unpinned
    assert [i.path for i in result] == ["b.jpg", "d.jpg", "a.jpg", "c.jpg"]


def test_quick_all_pinned():
    images = [
        _img("x.jpg", pinned=True),
        _img("y.jpg", pinned=True),
    ]
    result = build_play_order(images, shuffle=False, mode="quick")
    assert [i.path for i in result] == ["x.jpg", "y.jpg"]


def test_quick_no_pinned_shuffle_preserves_set():
    random.seed(42)
    images = [_img(f"{c}.jpg") for c in "abcdefghij"]
    result = build_play_order(images, shuffle=True, mode="quick")
    # Same images, possibly different order
    assert set(i.path for i in result) == set(i.path for i in images)
    assert len(result) == len(images)


def test_quick_no_pinned_shuffle_actually_shuffles():
    """With 10 images and a fixed seed, shuffled order should differ from input."""
    random.seed(0)
    images = [_img(f"{c}.jpg") for c in "abcdefghij"]
    result = build_play_order(images, shuffle=True, mode="quick")
    assert [i.path for i in result] != [i.path for i in images]


def test_quick_pinned_first_rest_shuffled():
    random.seed(1)
    images = [
        _img("a.jpg"),
        _img("P.jpg", pinned=True),
        _img("b.jpg"),
        _img("c.jpg"),
        _img("d.jpg"),
    ]
    result = build_play_order(images, shuffle=True, mode="quick")
    # Pinned first, regardless of shuffle
    assert result[0].path == "P.jpg"
    # Remaining four are the non-pinned set
    assert set(i.path for i in result[1:]) == {"a.jpg", "b.jpg", "c.jpg", "d.jpg"}


def test_quick_multiple_pinned_not_shuffled_among_themselves():
    """Pinned images keep their pin order even when shuffle=True."""
    random.seed(2)
    images = [
        _img("a.jpg"),
        _img("P1.jpg", pinned=True),
        _img("b.jpg"),
        _img("P2.jpg", pinned=True),
        _img("c.jpg"),
    ]
    # Run several times to be confident order is deterministic for pinned
    for seed in range(5):
        random.seed(seed)
        result = build_play_order(images, shuffle=True, mode="quick")
        assert result[0].path == "P1.jpg"
        assert result[1].path == "P2.jpg"


def test_class_no_pinned_tiers_ascending():
    images = [
        _img("a15m.jpg", timer=900),
        _img("a30s.jpg", timer=30),
        _img("b5m.jpg", timer=300),
        _img("b30s.jpg", timer=30),
    ]
    result = build_play_order(images, shuffle=False, mode="class")
    # 30s tier first, then 5m, then 15m
    assert [i.timer for i in result] == [30, 30, 300, 900]


def test_class_pinned_first_within_tier():
    """Pinned 15m image plays first within the 15m tier, not globally first."""
    images = [
        _img("s1.jpg", timer=30),
        _img("s2.jpg", timer=30),
        _img("m1.jpg", timer=300),
        _img("P15.jpg", timer=900, pinned=True),
        _img("m2.jpg", timer=300),
        _img("l1.jpg", timer=900),
    ]
    result = build_play_order(images, shuffle=False, mode="class")
    paths = [i.path for i in result]
    # Tiers ascending: 30s, then 5m, then 15m (pinned first in 15m)
    assert paths == ["s1.jpg", "s2.jpg", "m1.jpg", "m2.jpg", "P15.jpg", "l1.jpg"]


def test_class_multiple_pinned_across_different_tiers():
    images = [
        _img("s1.jpg", timer=30),
        _img("P30.jpg", timer=30, pinned=True),
        _img("m1.jpg", timer=300),
        _img("P5m.jpg", timer=300, pinned=True),
        _img("s2.jpg", timer=30),
    ]
    result = build_play_order(images, shuffle=False, mode="class")
    paths = [i.path for i in result]
    # 30s tier: P30 first, then s1, s2. 5m tier: P5m first, then m1.
    assert paths == ["P30.jpg", "s1.jpg", "s2.jpg", "P5m.jpg", "m1.jpg"]


def test_class_multiple_pinned_same_tier_preserve_order():
    images = [
        _img("a.jpg", timer=300),
        _img("P1.jpg", timer=300, pinned=True),
        _img("b.jpg", timer=300),
        _img("P2.jpg", timer=300, pinned=True),
    ]
    result = build_play_order(images, shuffle=False, mode="class")
    assert [i.path for i in result] == ["P1.jpg", "P2.jpg", "a.jpg", "b.jpg"]


def test_class_shuffle_only_shuffles_non_pinned_within_tier():
    random.seed(3)
    images = [
        _img("s1.jpg", timer=30),
        _img("s2.jpg", timer=30),
        _img("s3.jpg", timer=30),
        _img("PS.jpg", timer=30, pinned=True),
        _img("m1.jpg", timer=300),
    ]
    # Run across seeds to verify pinned deterministic, tier order stable
    for seed in range(5):
        random.seed(seed)
        result = build_play_order(images, shuffle=True, mode="class")
        timers = [i.timer for i in result]
        assert timers == [30, 30, 30, 30, 300]  # tier order stable
        assert result[0].path == "PS.jpg"       # pinned first in 30s tier
