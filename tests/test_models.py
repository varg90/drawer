import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.models import ImageItem

def test_image_item_defaults():
    item = ImageItem(path="C:/a.jpg")
    assert item.path == "C:/a.jpg"
    assert item.timer == 300

def test_image_item_custom_timer():
    item = ImageItem(path="C:/a.jpg", timer=60)
    assert item.timer == 60

def test_image_item_to_dict():
    item = ImageItem(path="C:/a.jpg", timer=120)
    assert item.to_dict() == {"path": "C:/a.jpg", "timer": 120}

def test_image_item_from_dict():
    item = ImageItem.from_dict({"path": "C:/b.png", "timer": 600})
    assert item.path == "C:/b.png"
    assert item.timer == 600

def test_image_item_from_dict_default_timer():
    item = ImageItem.from_dict({"path": "C:/c.gif"})
    assert item.timer == 300

def test_image_item_roundtrip():
    original = ImageItem(path="C:/test.webp", timer=42)
    restored = ImageItem.from_dict(original.to_dict())
    assert original == restored

def test_image_item_pinned_default():
    img = ImageItem(path="test.jpg")
    assert img.pinned is False


def test_image_item_pinned_true():
    img = ImageItem(path="test.jpg", timer=300, pinned=True)
    assert img.pinned is True
    d = img.to_dict()
    assert d["pinned"] is True
    restored = ImageItem.from_dict(d)
    assert restored.pinned is True


def test_image_item_pinned_not_in_dict_when_false():
    img = ImageItem(path="test.jpg")
    d = img.to_dict()
    assert "pinned" not in d
