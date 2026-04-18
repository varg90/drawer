import sys, os
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.models import ImageItem
from core.play_order import build_play_order


def _img(path, timer=300, pinned=False):
    return ImageItem(path=path, timer=timer, pinned=pinned)


def test_unknown_mode_raises():
    with pytest.raises(ValueError, match="unknown mode"):
        build_play_order([_img("a.jpg")], mode="bogus")


def test_empty_list_returns_empty():
    assert build_play_order([], mode="quick") == []
    assert build_play_order([], mode="class") == []


def test_quick_no_pinned_no_shuffle_is_identity():
    images = [_img("a.jpg"), _img("b.jpg"), _img("c.jpg")]
    result = build_play_order(images, mode="quick")
    assert [i.path for i in result] == ["a.jpg", "b.jpg", "c.jpg"]


def test_quick_one_pinned_plays_first():
    images = [
        _img("a.jpg"),
        _img("b.jpg", pinned=True),
        _img("c.jpg"),
    ]
    result = build_play_order(images, mode="quick")
    assert [i.path for i in result] == ["b.jpg", "a.jpg", "c.jpg"]


def test_quick_multiple_pinned_preserve_pin_order():
    images = [
        _img("a.jpg"),
        _img("b.jpg", pinned=True),
        _img("c.jpg"),
        _img("d.jpg", pinned=True),
    ]
    result = build_play_order(images, mode="quick")
    # Pinned first (in their original relative order), then unpinned
    assert [i.path for i in result] == ["b.jpg", "d.jpg", "a.jpg", "c.jpg"]


def test_quick_all_pinned():
    images = [
        _img("x.jpg", pinned=True),
        _img("y.jpg", pinned=True),
    ]
    result = build_play_order(images, mode="quick")
    assert [i.path for i in result] == ["x.jpg", "y.jpg"]


def test_class_no_pinned_tiers_ascending():
    images = [
        _img("a15m.jpg", timer=900),
        _img("a30s.jpg", timer=30),
        _img("b5m.jpg", timer=300),
        _img("b30s.jpg", timer=30),
    ]
    result = build_play_order(images, mode="class")
    # 30s tier first, then 5m, then 15m
    assert [i.timer for i in result] == [30, 30, 300, 900]


def test_class_pin_flag_does_not_reorder_tier():
    """Pin flag has no ordering effect in class mode — list order is preserved within tier."""
    images = [
        _img("s1.jpg", timer=30),
        _img("s2.jpg", timer=30),
        _img("m1.jpg", timer=300),
        _img("P15.jpg", timer=900, pinned=True),
        _img("m2.jpg", timer=300),
        _img("l1.jpg", timer=900),
    ]
    result = build_play_order(images, mode="class")
    paths = [i.path for i in result]
    # Tier-ascending, list-order within each tier. Pin is ignored.
    assert paths == ["s1.jpg", "s2.jpg", "m1.jpg", "m2.jpg", "P15.jpg", "l1.jpg"]


def test_class_multiple_pinned_across_different_tiers():
    """Class mode ignores pin flag. Images play in list order within each tier."""
    images = [
        _img("s1.jpg", timer=30),
        _img("P30.jpg", timer=30, pinned=True),
        _img("m1.jpg", timer=300),
        _img("P5m.jpg", timer=300, pinned=True),
        _img("s2.jpg", timer=30),
    ]
    result = build_play_order(images, mode="class")
    paths = [i.path for i in result]
    # 30s tier: s1, P30, s2 (list order, pin ignored).
    # 5m tier: m1, P5m (list order, pin ignored).
    assert paths == ["s1.jpg", "P30.jpg", "s2.jpg", "m1.jpg", "P5m.jpg"]


def test_class_multiple_pinned_same_tier_preserve_order():
    """Class mode ignores pin flag. Same-tier images play in list order."""
    images = [
        _img("a.jpg", timer=300),
        _img("P1.jpg", timer=300, pinned=True),
        _img("b.jpg", timer=300),
        _img("P2.jpg", timer=300, pinned=True),
    ]
    result = build_play_order(images, mode="class")
    assert [i.path for i in result] == ["a.jpg", "P1.jpg", "b.jpg", "P2.jpg"]


def test_class_mode_ignores_pin_flag():
    """Class mode output is invariant under pin flag changes."""
    images_with_pins = [
        _img("a.jpg", timer=30, pinned=True),
        _img("b.jpg", timer=30),
        _img("c.jpg", timer=300),
        _img("d.jpg", timer=300, pinned=True),
    ]
    images_without_pins = [
        _img("a.jpg", timer=30),
        _img("b.jpg", timer=30),
        _img("c.jpg", timer=300),
        _img("d.jpg", timer=300),
    ]
    pinned_result = [i.path for i in build_play_order(images_with_pins, mode="class")]
    plain_result = [i.path for i in build_play_order(images_without_pins, mode="class")]
    assert pinned_result == plain_result
