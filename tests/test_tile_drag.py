"""Unit tests for tile-drag helpers — pure Python, no Qt."""

from core.models import ImageItem
from ui.editor_panel import (
    _compute_insertion_index,
    _filter_selection_by_zone,
    _apply_tile_drop,
)


def _img(path, pinned=False, timer=60):
    return ImageItem(path=path, timer=timer, pinned=pinned)


# ------------------------------------------------------------------
# _compute_insertion_index
# ------------------------------------------------------------------

def test_insertion_index_empty_grid():
    assert _compute_insertion_index((50, 50), []) == 0


def test_insertion_index_before_first_tile():
    rects = [(0, 0, 0, 80, 80), (1, 90, 0, 80, 80)]  # (idx, x, y, w, h)
    assert _compute_insertion_index((5, 40), rects) == 0


def test_insertion_index_between_two_tiles():
    rects = [(0, 0, 0, 80, 80), (1, 90, 0, 80, 80)]
    # Cursor past midline of first tile → insert between (index 1)
    assert _compute_insertion_index((50, 40), rects) == 1


def test_insertion_index_after_last_tile():
    rects = [(0, 0, 0, 80, 80), (1, 90, 0, 80, 80)]
    assert _compute_insertion_index((200, 40), rects) == 2


def test_insertion_index_second_row():
    rects = [
        (0, 0, 0, 80, 80),
        (1, 90, 0, 80, 80),
        (2, 0, 90, 80, 80),
        (3, 90, 90, 80, 80),
    ]
    # Cursor on second row, between the two tiles → index 3
    assert _compute_insertion_index((50, 130), rects) == 3


# ------------------------------------------------------------------
# _filter_selection_by_zone
# ------------------------------------------------------------------

def test_filter_selection_keeps_same_zone():
    images = [_img("a", pinned=True), _img("b", pinned=True),
              _img("c"), _img("d")]
    # Selection: indices 0, 1, 2 (two pinned + one non-pinned)
    # Source zone: pinned (index 0 pressed)
    assert _filter_selection_by_zone([0, 1, 2], source_is_pinned=True,
                                     images=images) == [0, 1]


def test_filter_selection_keeps_non_pinned():
    images = [_img("a", pinned=True), _img("b"), _img("c"), _img("d")]
    # Selection 0, 2, 3 — source non-pinned (index 2 pressed)
    assert _filter_selection_by_zone([0, 2, 3], source_is_pinned=False,
                                     images=images) == [2, 3]


def test_filter_selection_single():
    images = [_img("a"), _img("b")]
    assert _filter_selection_by_zone([0], source_is_pinned=False,
                                     images=images) == [0]


# ------------------------------------------------------------------
# _apply_tile_drop
# ------------------------------------------------------------------

def test_apply_drop_within_non_pinned_zone():
    """Reorder within non-pinned zone. No pin changes."""
    images = [_img("p", pinned=True), _img("a"), _img("b"), _img("c")]
    # Move "c" (index 3) to just before "a" — insert index 1 in non-pinned zone
    new = _apply_tile_drop(images, source_indices=[3], insert_idx=1,
                           target_is_pinned=False)
    assert [i.path for i in new] == ["p", "c", "a", "b"]
    assert [i.pinned for i in new] == [True, False, False, False]


def test_apply_drop_within_pinned_zone():
    """Reorder within pinned zone. No pin changes."""
    images = [_img("p1", pinned=True), _img("p2", pinned=True),
              _img("p3", pinned=True), _img("a")]
    # Move "p3" to position 0 among pinned
    new = _apply_tile_drop(images, source_indices=[2], insert_idx=0,
                           target_is_pinned=True)
    assert [i.path for i in new] == ["p3", "p1", "p2", "a"]
    assert [i.pinned for i in new] == [True, True, True, False]


def test_apply_drop_non_pinned_into_pinned_zone():
    """Cross-zone: non-pinned → pinned. Item becomes pinned."""
    images = [_img("p", pinned=True), _img("a"), _img("b")]
    # Drop "b" (index 2) into pinned zone at insert_idx 1 (after "p")
    new = _apply_tile_drop(images, source_indices=[2], insert_idx=1,
                           target_is_pinned=True)
    assert [i.path for i in new] == ["p", "b", "a"]
    assert [i.pinned for i in new] == [True, True, False]


def test_apply_drop_pinned_into_non_pinned_zone():
    """Cross-zone: pinned → non-pinned. Item becomes unpinned."""
    images = [_img("p1", pinned=True), _img("p2", pinned=True),
              _img("a"), _img("b")]
    # Drop "p1" (index 0) into non-pinned zone at insert_idx 3
    new = _apply_tile_drop(images, source_indices=[0], insert_idx=3,
                           target_is_pinned=False)
    assert [i.path for i in new] == ["p2", "a", "p1", "b"]
    assert [i.pinned for i in new] == [True, False, False, False]


def test_apply_drop_multi_select_non_pinned_into_pinned():
    """Multi-select cross-zone drop. All become pinned."""
    images = [_img("p", pinned=True), _img("a"), _img("b"), _img("c")]
    new = _apply_tile_drop(images, source_indices=[1, 2], insert_idx=1,
                           target_is_pinned=True)
    # "a" and "b" join the pinned block after "p"
    assert [i.path for i in new] == ["p", "a", "b", "c"]
    assert [i.pinned for i in new] == [True, True, True, False]


def test_apply_drop_preserves_pinned_contiguous_invariant():
    """After any drop, pinned tiles are contiguous at the head."""
    images = [_img("p1", pinned=True), _img("a"), _img("p2", pinned=True),
              _img("b")]
    # (Pathological starting state — pinned not contiguous. Apply a drop and
    # verify the result is normalized.)
    new = _apply_tile_drop(images, source_indices=[3], insert_idx=4,
                           target_is_pinned=False)
    # All pinned come first in result regardless of input order
    pinned = [i for i in new if i.pinned]
    unpinned = [i for i in new if not i.pinned]
    assert new == pinned + unpinned


def test_apply_drop_same_position_noop():
    """Dropping at the exact source position yields the original list."""
    images = [_img("p", pinned=True), _img("a"), _img("b")]
    new = _apply_tile_drop(images, source_indices=[1], insert_idx=1,
                           target_is_pinned=False)
    assert [i.path for i in new] == ["p", "a", "b"]
