import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import tempfile
from core.cloud.cache import CacheManager
from core.cloud.base import CloudFile

def _make_cache(tmp):
    return CacheManager(cache_dir=tmp)

def _make_file(name="photo.jpg", url="https://example.com/photo.jpg"):
    return CloudFile(name=name, download_url=url, size=0, preview_url="")

def test_get_missing():
    with tempfile.TemporaryDirectory() as tmp:
        cm = _make_cache(tmp)
        f = _make_file()
        assert cm.get(f) is None

def test_put_and_get():
    with tempfile.TemporaryDirectory() as tmp:
        cm = _make_cache(tmp)
        f = _make_file()
        path = cm.put(f, b"fake image data")
        assert os.path.isfile(path)
        assert cm.get(f) == path

def test_put_creates_dir():
    with tempfile.TemporaryDirectory() as tmp:
        cache_dir = os.path.join(tmp, "subcache")
        cm = CacheManager(cache_dir=cache_dir)
        f = _make_file()
        path = cm.put(f, b"data")
        assert os.path.isfile(path)

def test_clear():
    with tempfile.TemporaryDirectory() as tmp:
        cm = _make_cache(tmp)
        cm.put(_make_file(), b"data")
        cm.clear()
        assert cm.size() == 0
        assert cm.get(_make_file()) is None

def test_size():
    with tempfile.TemporaryDirectory() as tmp:
        cm = _make_cache(tmp)
        cm.put(_make_file("a.jpg", "http://a"), b"12345")
        cm.put(_make_file("b.jpg", "http://b"), b"67890")
        assert cm.size() == 10

def test_size_empty():
    with tempfile.TemporaryDirectory() as tmp:
        cm = _make_cache(tmp)
        assert cm.size() == 0

def test_different_urls_different_files():
    with tempfile.TemporaryDirectory() as tmp:
        cm = _make_cache(tmp)
        f1 = _make_file("photo.jpg", "https://example.com/1")
        f2 = _make_file("photo.jpg", "https://example.com/2")
        p1 = cm.put(f1, b"data1")
        p2 = cm.put(f2, b"data2")
        assert p1 != p2
        assert cm.get(f1) == p1
        assert cm.get(f2) == p2

def test_format_size_bytes():
    assert CacheManager.format_size(500) == "500 Б"

def test_format_size_kb():
    assert CacheManager.format_size(2048) == "2.0 КБ"

def test_format_size_mb():
    assert CacheManager.format_size(5 * 1024 * 1024) == "5.0 МБ"

def test_format_size_zero():
    assert CacheManager.format_size(0) == "0 Б"
