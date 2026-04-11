import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ui.editor_panel import _sort_group_items


def _make_item(path, pinned=False):
    return type("I", (), {"pinned": pinned, "path": path})()


def test_pinned_images_sort_first():
    items = [
        (0, _make_item("a.jpg", pinned=False)),
        (1, _make_item("b.jpg", pinned=True)),
        (2, _make_item("c.jpg", pinned=False)),
        (3, _make_item("d.jpg", pinned=True)),
    ]
    result = _sort_group_items(items)
    assert result[0][1].path == "b.jpg"
    assert result[1][1].path == "d.jpg"
    assert result[2][1].path == "a.jpg"
    assert result[3][1].path == "c.jpg"


def test_pinned_sort_preserves_order():
    items = [
        (0, _make_item("1.jpg", pinned=True)),
        (1, _make_item("2.jpg", pinned=False)),
        (2, _make_item("3.jpg", pinned=True)),
    ]
    result = _sort_group_items(items)
    assert [r[1].path for r in result] == ["1.jpg", "3.jpg", "2.jpg"]


def test_all_pinned_preserves_order():
    items = [
        (0, _make_item("x.jpg", pinned=True)),
        (1, _make_item("y.jpg", pinned=True)),
    ]
    result = _sort_group_items(items)
    assert [r[1].path for r in result] == ["x.jpg", "y.jpg"]


def test_no_pinned_preserves_order():
    items = [
        (0, _make_item("a.jpg")),
        (1, _make_item("b.jpg")),
    ]
    result = _sort_group_items(items)
    assert [r[1].path for r in result] == ["a.jpg", "b.jpg"]


def test_empty_list():
    assert _sort_group_items([]) == []
