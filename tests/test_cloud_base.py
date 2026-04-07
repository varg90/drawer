import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.cloud import detect_provider
from core.cloud.base import CloudFile

def test_cloudfile_creation():
    f = CloudFile(name="photo.jpg", download_url="https://example.com/photo.jpg", size=1024, preview_url="")
    assert f.name == "photo.jpg"
    assert f.size == 1024

def test_cloudfile_is_image_true():
    f = CloudFile(name="art.png", download_url="", size=0, preview_url="")
    assert f.is_image() is True

def test_cloudfile_is_image_false():
    f = CloudFile(name="doc.pdf", download_url="", size=0, preview_url="")
    assert f.is_image() is False

def test_cloudfile_is_image_case_insensitive():
    f = CloudFile(name="ART.JPG", download_url="", size=0, preview_url="")
    assert f.is_image() is True

def test_detect_yandex_disk():
    p = detect_provider("https://disk.yandex.ru/d/abc123")
    assert p is not None
    assert p.name == "yandex"

def test_detect_yandex_disk_variant():
    p = detect_provider("https://yadi.sk/d/abc123")
    assert p is not None
    assert p.name == "yandex"

def test_detect_google_drive_folder():
    p = detect_provider("https://drive.google.com/drive/folders/1abc123")
    assert p is not None
    assert p.name == "google"

def test_detect_google_drive_file():
    p = detect_provider("https://drive.google.com/file/d/1abc123/view")
    assert p is not None
    assert p.name == "google"

def test_detect_unknown():
    assert detect_provider("https://example.com/images") is None

def test_detect_empty():
    assert detect_provider("") is None

def test_detect_garbage():
    assert detect_provider("not a url") is None
