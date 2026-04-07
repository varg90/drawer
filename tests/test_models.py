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

def test_image_item_source_url_default():
    item = ImageItem(path="C:/a.jpg")
    assert item.source_url == ""

def test_image_item_source_url_custom():
    item = ImageItem(path="C:/a.jpg", source_url="https://disk.yandex.ru/d/abc")
    assert item.source_url == "https://disk.yandex.ru/d/abc"

def test_image_item_to_dict_with_source_url():
    item = ImageItem(path="C:/a.jpg", timer=60, source_url="https://example.com")
    d = item.to_dict()
    assert d["source_url"] == "https://example.com"

def test_image_item_from_dict_with_source_url():
    item = ImageItem.from_dict({"path": "C:/a.jpg", "source_url": "https://example.com"})
    assert item.source_url == "https://example.com"

def test_image_item_from_dict_without_source_url():
    item = ImageItem.from_dict({"path": "C:/a.jpg", "timer": 60})
    assert item.source_url == ""

def test_image_item_roundtrip_with_source_url():
    original = ImageItem(path="C:/a.jpg", timer=42, source_url="https://ya.ru/d/x")
    restored = ImageItem.from_dict(original.to_dict())
    assert original == restored
