import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from unittest.mock import patch, MagicMock
from core.cloud.yandex import YandexDiskProvider
from core.cloud.base import CloudFile

FAKE_RESPONSE_FOLDER = {
    "_embedded": {
        "items": [
            {"name": "art.jpg", "file": "https://download/art.jpg", "size": 5000,
             "preview": "https://preview/art.jpg", "media_type": "image"},
            {"name": "sketch.png", "file": "https://download/sketch.png", "size": 3000,
             "preview": "https://preview/sketch.png", "media_type": "image"},
            {"name": "notes.txt", "file": "https://download/notes.txt", "size": 100,
             "preview": "", "media_type": "document"},
        ],
        "total": 3,
    },
    "type": "dir",
}

FAKE_RESPONSE_FILE = {
    "name": "single.jpg",
    "file": "https://download/single.jpg",
    "size": 8000,
    "preview": "https://preview/single.jpg",
    "media_type": "image",
    "type": "file",
}

def _mock_get(json_data, status=200):
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    if status >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status}")
    return resp

@patch("core.cloud.yandex.requests.get")
def test_list_folder(mock_get):
    mock_get.return_value = _mock_get(FAKE_RESPONSE_FOLDER)
    p = YandexDiskProvider()
    files = p.list_files("https://disk.yandex.ru/d/abc123")
    assert len(files) == 2
    assert files[0].name == "art.jpg"
    assert files[1].name == "sketch.png"
    assert files[0].download_url == "https://download/art.jpg"
    assert files[0].size == 5000

@patch("core.cloud.yandex.requests.get")
def test_list_single_file(mock_get):
    mock_get.return_value = _mock_get(FAKE_RESPONSE_FILE)
    p = YandexDiskProvider()
    files = p.list_files("https://disk.yandex.ru/d/xyz")
    assert len(files) == 1
    assert files[0].name == "single.jpg"

@patch("core.cloud.yandex.requests.get")
def test_list_error(mock_get):
    mock_get.return_value = _mock_get({}, status=404)
    p = YandexDiskProvider()
    try:
        p.list_files("https://disk.yandex.ru/d/bad")
        assert False, "Should have raised"
    except Exception:
        pass

@patch("core.cloud.yandex.requests.get")
def test_download(mock_get):
    resp = MagicMock()
    resp.content = b"fake image bytes"
    resp.raise_for_status = MagicMock()
    mock_get.return_value = resp
    p = YandexDiskProvider()
    f = CloudFile(name="a.jpg", download_url="https://download/a.jpg", size=0, preview_url="")
    import tempfile
    dest = os.path.join(tempfile.gettempdir(), "test_dl_a.jpg")
    result = p.download(f, dest)
    assert result == dest
    assert os.path.isfile(dest)
    with open(dest, "rb") as fh:
        assert fh.read() == b"fake image bytes"
    os.unlink(dest)
