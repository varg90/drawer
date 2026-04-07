import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from unittest.mock import patch, MagicMock
from core.cloud.google import GoogleDriveProvider

FAKE_FOLDER_RESPONSE = {
    "files": [
        {"id": "f1", "name": "photo.jpg", "mimeType": "image/jpeg", "size": "4000"},
        {"id": "f2", "name": "sketch.png", "mimeType": "image/png", "size": "3000"},
        {"id": "f3", "name": "readme.txt", "mimeType": "text/plain", "size": "100"},
    ]
}

FAKE_FILE_RESPONSE = {
    "id": "f1", "name": "single.jpg", "mimeType": "image/jpeg", "size": "8000"
}

def _mock_get(json_data, status=200):
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    if status >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status}")
    return resp

@patch("core.cloud.google.requests.get")
def test_list_folder(mock_get):
    mock_get.return_value = _mock_get(FAKE_FOLDER_RESPONSE)
    p = GoogleDriveProvider()
    files = p.list_files("https://drive.google.com/drive/folders/1abc123")
    assert len(files) == 2
    assert files[0].name == "photo.jpg"
    assert files[1].name == "sketch.png"

@patch("core.cloud.google.requests.get")
def test_list_single_file(mock_get):
    mock_get.return_value = _mock_get(FAKE_FILE_RESPONSE)
    p = GoogleDriveProvider()
    files = p.list_files("https://drive.google.com/file/d/f1/view")
    assert len(files) == 1
    assert files[0].name == "single.jpg"

@patch("core.cloud.google.requests.get")
def test_list_error(mock_get):
    mock_get.return_value = _mock_get({}, status=403)
    p = GoogleDriveProvider()
    try:
        p.list_files("https://drive.google.com/drive/folders/bad")
        assert False, "Should have raised"
    except Exception:
        pass

@patch("core.cloud.google.requests.get")
def test_download(mock_get):
    resp = MagicMock()
    resp.content = b"image bytes"
    resp.raise_for_status = MagicMock()
    mock_get.return_value = resp
    p = GoogleDriveProvider()
    from core.cloud.base import CloudFile
    f = CloudFile(name="a.jpg", download_url="https://dl/a.jpg", size=0, preview_url="")
    import tempfile
    dest = os.path.join(tempfile.gettempdir(), "test_dl_g.jpg")
    result = p.download(f, dest)
    assert result == dest
    with open(dest, "rb") as fh:
        assert fh.read() == b"image bytes"
    os.unlink(dest)

def test_extract_folder_id():
    p = GoogleDriveProvider()
    assert p._extract_id("https://drive.google.com/drive/folders/1abc123") == "1abc123"
    assert p._extract_id("https://drive.google.com/drive/folders/1abc123?usp=sharing") == "1abc123"

def test_extract_file_id():
    p = GoogleDriveProvider()
    assert p._extract_id("https://drive.google.com/file/d/1xyz789/view") == "1xyz789"
    assert p._extract_id("https://drive.google.com/file/d/1xyz789/view?usp=sharing") == "1xyz789"
