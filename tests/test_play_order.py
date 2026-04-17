import sys, os
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
