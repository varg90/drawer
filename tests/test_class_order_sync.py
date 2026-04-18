"""Unit tests for the _class_order membership sync helper."""

from core.models import ImageItem
from ui.settings_window import _sync_class_order_to_images


def _img(path, timer=60, pinned=False):
    return ImageItem(path=path, timer=timer, pinned=pinned)


def test_none_passthrough():
    """When class_order is None, return None (no shuffle active)."""
    images = [_img("a"), _img("b")]
    assert _sync_class_order_to_images(None, images) is None


def test_same_membership_preserves_order():
    """Both lists contain the same set → class_order order is kept."""
    a, b, c = _img("a"), _img("b"), _img("c")
    images = [a, b, c]
    class_order = [c, a, b]
    result = _sync_class_order_to_images(class_order, images)
    assert result == [c, a, b]


def test_deleted_image_dropped():
    """An image present in class_order but missing from images is filtered out."""
    a, b, c = _img("a"), _img("b"), _img("c")
    images = [a, c]
    class_order = [c, b, a]
    result = _sync_class_order_to_images(class_order, images)
    assert result == [c, a]


def test_added_image_appended():
    """An image in images but not yet in class_order is appended at the end."""
    a, b, c = _img("a"), _img("b"), _img("c")
    images = [a, b, c]
    class_order = [b, a]
    result = _sync_class_order_to_images(class_order, images)
    assert result == [b, a, c]


def test_combined_add_and_delete():
    """Mixed: one deleted, one added. Survivors keep order, new at end."""
    a, b, c, d = _img("a"), _img("b"), _img("c"), _img("d")
    images = [a, c, d]
    class_order = [b, c, a]
    result = _sync_class_order_to_images(class_order, images)
    assert result == [c, a, d]


def test_multiple_added_appended_in_images_order():
    """Two new images both get appended in self.images order."""
    a, b, c, d = _img("a"), _img("b"), _img("c"), _img("d")
    images = [a, b, c, d]
    class_order = [b, a]
    result = _sync_class_order_to_images(class_order, images)
    assert result == [b, a, c, d]


def test_empty_images():
    """Empty images → empty class_order."""
    a, b = _img("a"), _img("b")
    result = _sync_class_order_to_images([a, b], [])
    assert result == []


def test_empty_class_order_populates_from_images():
    """Empty class_order with a non-empty images list appends all images."""
    a, b = _img("a"), _img("b")
    result = _sync_class_order_to_images([], [a, b])
    assert result == [a, b]


def test_preserves_item_identity_not_value():
    """Equal-by-value but distinct objects are tracked by identity (id())."""
    a1 = _img("a")
    a2 = _img("a")
    images = [a2]
    class_order = [a1]
    result = _sync_class_order_to_images(class_order, images)
    assert result == [a2]
    assert result[0] is a2
