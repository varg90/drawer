# Cloud Image Loading Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users load images from public Yandex Disk and Google Drive links via a "URL" button in the image editor.

**Architecture:** Modular provider system in `core/cloud/` — one file per service, shared base class. A `CacheManager` stores downloaded files in `APP_DIR/cache/`. A new `UrlDialog` in `ui/` handles the full flow: URL input, file list with checkboxes, download with progress. `ImageItem` gains an optional `source_url` field for cloud files.

**Tech Stack:** Python 3.14, PyQt6, requests library, Yandex Disk public API, Google Drive API v3.

**Spec:** `docs/superpowers/specs/2026-04-07-cloud-image-loading-design.md`

---

## File Structure

```
core/cloud/__init__.py    — detect_provider(url) dispatcher
core/cloud/base.py        — CloudProvider base class, CloudFile dataclass
core/cloud/cache.py       — CacheManager (save/load/clear/size)
core/cloud/yandex.py      — YandexDiskProvider
core/cloud/google.py      — GoogleDriveProvider
ui/url_dialog.py          — UrlDialog (URL input + file picker + download)
core/models.py            — Add source_url field to ImageItem (modify)
ui/image_editor_window.py — Add "URL" button (modify)
ui/settings_window.py     — Add "Очистить кеш" button (modify)
tests/test_cloud_base.py  — Tests for detect_provider, CloudFile
tests/test_cache.py       — Tests for CacheManager
tests/test_yandex.py      — Tests for YandexDiskProvider
tests/test_google.py      — Tests for GoogleDriveProvider
tests/test_models.py      — Add tests for source_url (modify)
```

---

### Task 1: Install requests & update ImageItem model

**Files:**
- Modify: `core/models.py`
- Modify: `tests/test_models.py`

- [ ] **Step 1: Install requests**

Run:
```bash
python -m pip install requests
```

- [ ] **Step 2: Write failing tests for source_url field**

Add to `tests/test_models.py`:

```python
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
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_models.py -v`
Expected: FAIL — `source_url` not defined

- [ ] **Step 4: Update ImageItem**

Replace `core/models.py` with:

```python
from dataclasses import dataclass

@dataclass
class ImageItem:
    path: str
    timer: int = 300
    source_url: str = ""

    def to_dict(self):
        d = {"path": self.path, "timer": self.timer}
        if self.source_url:
            d["source_url"] = self.source_url
        return d

    @classmethod
    def from_dict(cls, d):
        return cls(
            path=d["path"],
            timer=d.get("timer", 300),
            source_url=d.get("source_url", ""),
        )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_models.py -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add core/models.py tests/test_models.py
git commit -m "feat: add source_url field to ImageItem for cloud images"
```

---

### Task 2: CloudProvider base class and detect_provider

**Files:**
- Create: `core/cloud/__init__.py`
- Create: `core/cloud/base.py`
- Create: `tests/test_cloud_base.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_cloud_base.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_cloud_base.py -v`
Expected: FAIL — modules don't exist

- [ ] **Step 3: Create base.py**

Create `core/cloud/base.py`:

```python
import os
from dataclasses import dataclass
from core.constants import SUPPORTED_FORMATS


@dataclass
class CloudFile:
    name: str
    download_url: str
    size: int
    preview_url: str

    def is_image(self):
        ext = os.path.splitext(self.name)[1].lower()
        return ext in SUPPORTED_FORMATS


class CloudProvider:
    name = ""

    def list_files(self, url):
        """Return list of CloudFile from a public URL. Raises on error."""
        raise NotImplementedError

    def download(self, cloud_file, dest_path):
        """Download cloud_file to dest_path. Returns dest_path."""
        raise NotImplementedError
```

- [ ] **Step 4: Create __init__.py with detect_provider**

Create `core/cloud/__init__.py`:

```python
import re


def detect_provider(url):
    if not url or not isinstance(url, str):
        return None

    # Yandex Disk: disk.yandex.ru/d/... or yadi.sk/d/...
    if re.search(r"(disk\.yandex\.\w+/d/|yadi\.sk/d/)", url):
        from core.cloud.yandex import YandexDiskProvider
        return YandexDiskProvider()

    # Google Drive: drive.google.com/drive/folders/... or drive.google.com/file/d/...
    if re.search(r"drive\.google\.com/(drive/folders/|file/d/)", url):
        from core.cloud.google import GoogleDriveProvider
        return GoogleDriveProvider()

    return None
```

- [ ] **Step 5: Create stub providers so imports work**

Create `core/cloud/yandex.py`:

```python
from core.cloud.base import CloudProvider


class YandexDiskProvider(CloudProvider):
    name = "yandex"

    def list_files(self, url):
        raise NotImplementedError

    def download(self, cloud_file, dest_path):
        raise NotImplementedError
```

Create `core/cloud/google.py`:

```python
from core.cloud.base import CloudProvider


class GoogleDriveProvider(CloudProvider):
    name = "google"

    def list_files(self, url):
        raise NotImplementedError

    def download(self, cloud_file, dest_path):
        raise NotImplementedError
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest tests/test_cloud_base.py -v`
Expected: all PASS

- [ ] **Step 7: Commit**

```bash
git add core/cloud/ tests/test_cloud_base.py
git commit -m "feat: add CloudProvider base, CloudFile dataclass, detect_provider"
```

---

### Task 3: CacheManager

**Files:**
- Create: `core/cloud/cache.py`
- Create: `tests/test_cache.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_cache.py`:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import tempfile
import shutil
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_cache.py -v`
Expected: FAIL — module doesn't exist

- [ ] **Step 3: Implement CacheManager**

Create `core/cloud/cache.py`:

```python
import os
import hashlib


class CacheManager:
    def __init__(self, cache_dir=None):
        if cache_dir is None:
            from core.session import APP_DIR
            cache_dir = os.path.join(APP_DIR, "cache")
        self._dir = cache_dir

    def _key(self, cloud_file):
        h = hashlib.md5(cloud_file.download_url.encode()).hexdigest()[:12]
        return f"{h}_{cloud_file.name}"

    def get(self, cloud_file):
        path = os.path.join(self._dir, self._key(cloud_file))
        return path if os.path.isfile(path) else None

    def put(self, cloud_file, data):
        os.makedirs(self._dir, exist_ok=True)
        path = os.path.join(self._dir, self._key(cloud_file))
        with open(path, "wb") as f:
            f.write(data)
        return path

    def clear(self):
        if not os.path.isdir(self._dir):
            return
        for name in os.listdir(self._dir):
            path = os.path.join(self._dir, name)
            if os.path.isfile(path):
                os.remove(path)

    def size(self):
        if not os.path.isdir(self._dir):
            return 0
        total = 0
        for name in os.listdir(self._dir):
            path = os.path.join(self._dir, name)
            if os.path.isfile(path):
                total += os.path.getsize(path)
        return total

    @staticmethod
    def format_size(n):
        if n < 1024:
            return f"{n} Б"
        elif n < 1024 * 1024:
            return f"{n / 1024:.1f} КБ"
        else:
            return f"{n / (1024 * 1024):.1f} МБ"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_cache.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add core/cloud/cache.py tests/test_cache.py
git commit -m "feat: add CacheManager for cloud image caching"
```

---

### Task 4: YandexDiskProvider

**Files:**
- Modify: `core/cloud/yandex.py`
- Create: `tests/test_yandex.py`

- [ ] **Step 1: Write tests with mocked HTTP**

Create `tests/test_yandex.py`:

```python
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
    assert len(files) == 2  # only images
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_yandex.py -v`
Expected: FAIL — NotImplementedError

- [ ] **Step 3: Implement YandexDiskProvider**

Replace `core/cloud/yandex.py`:

```python
import requests
from core.cloud.base import CloudProvider, CloudFile

API_URL = "https://cloud-api.yandex.net/v1/disk/public/resources"
LIMIT = 150


class YandexDiskProvider(CloudProvider):
    name = "yandex"

    def list_files(self, url):
        files = []
        offset = 0
        while True:
            resp = requests.get(API_URL, params={
                "public_key": url,
                "limit": LIMIT,
                "offset": offset,
            })
            resp.raise_for_status()
            data = resp.json()

            if data.get("type") == "file":
                cf = self._to_cloud_file(data)
                if cf and cf.is_image():
                    return [cf]
                return []

            items = data.get("_embedded", {}).get("items", [])
            for item in items:
                cf = self._to_cloud_file(item)
                if cf and cf.is_image():
                    files.append(cf)

            total = data.get("_embedded", {}).get("total", 0)
            offset += LIMIT
            if offset >= total:
                break

        return files

    def download(self, cloud_file, dest_path):
        resp = requests.get(cloud_file.download_url)
        resp.raise_for_status()
        with open(dest_path, "wb") as f:
            f.write(resp.content)
        return dest_path

    def _to_cloud_file(self, item):
        dl = item.get("file", "")
        if not dl:
            return None
        return CloudFile(
            name=item.get("name", ""),
            download_url=dl,
            size=item.get("size", 0),
            preview_url=item.get("preview", ""),
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_yandex.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add core/cloud/yandex.py tests/test_yandex.py
git commit -m "feat: implement YandexDiskProvider for public links"
```

---

### Task 5: GoogleDriveProvider

**Files:**
- Modify: `core/cloud/google.py`
- Create: `tests/test_google.py`

- [ ] **Step 1: Write tests with mocked HTTP**

Create `tests/test_google.py`:

```python
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
    assert len(files) == 2  # only images
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_google.py -v`
Expected: FAIL — NotImplementedError

- [ ] **Step 3: Implement GoogleDriveProvider**

Replace `core/cloud/google.py`:

```python
import re
import requests
from core.cloud.base import CloudProvider, CloudFile

API_KEY = "AIzaSyDummyKeyReplaceLater"
FILES_URL = "https://www.googleapis.com/drive/v3/files"


class GoogleDriveProvider(CloudProvider):
    name = "google"

    def list_files(self, url):
        file_id = self._extract_id(url)
        if not file_id:
            raise ValueError("Cannot extract ID from Google Drive URL")

        is_folder = "/drive/folders/" in url

        if is_folder:
            return self._list_folder(file_id)
        else:
            return self._list_single(file_id)

    def _list_folder(self, folder_id):
        resp = requests.get(FILES_URL, params={
            "q": f"'{folder_id}' in parents and trashed=false",
            "key": API_KEY,
            "fields": "files(id,name,mimeType,size)",
            "pageSize": 1000,
        })
        resp.raise_for_status()
        files = []
        for item in resp.json().get("files", []):
            if item.get("mimeType", "").startswith("image/"):
                files.append(self._to_cloud_file(item))
        return files

    def _list_single(self, file_id):
        resp = requests.get(f"{FILES_URL}/{file_id}", params={
            "key": API_KEY,
            "fields": "id,name,mimeType,size",
        })
        resp.raise_for_status()
        item = resp.json()
        if item.get("mimeType", "").startswith("image/"):
            return [self._to_cloud_file(item)]
        return []

    def download(self, cloud_file, dest_path):
        resp = requests.get(cloud_file.download_url)
        resp.raise_for_status()
        with open(dest_path, "wb") as f:
            f.write(resp.content)
        return dest_path

    def _to_cloud_file(self, item):
        fid = item["id"]
        return CloudFile(
            name=item.get("name", ""),
            download_url=f"{FILES_URL}/{fid}?alt=media&key={API_KEY}",
            size=int(item.get("size", 0)),
            preview_url=f"https://drive.google.com/thumbnail?id={fid}&sz=w200",
        )

    def _extract_id(self, url):
        m = re.search(r"/folders/([^/?]+)", url)
        if m:
            return m.group(1)
        m = re.search(r"/file/d/([^/?]+)", url)
        if m:
            return m.group(1)
        return None
```

**Note:** The `API_KEY` is a placeholder. Google Drive API requires a key. This will be addressed when setting up the real key — either bundled or user-provided in settings. For now tests mock HTTP so the key value doesn't matter.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_google.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add core/cloud/google.py tests/test_google.py
git commit -m "feat: implement GoogleDriveProvider for public links"
```

---

### Task 6: UrlDialog — file picker with previews and download

**Files:**
- Create: `ui/url_dialog.py`

This is a UI component — no unit tests (would require QApplication). Tested manually.

- [ ] **Step 1: Create UrlDialog**

Create `ui/url_dialog.py`:

```python
import os
import requests
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
                              QPushButton, QLabel, QListWidget, QListWidgetItem,
                              QProgressBar)
from PyQt6.QtGui import QPixmap, QIcon, QImage
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal
from core.cloud import detect_provider
from core.cloud.cache import CacheManager
from core.cloud.base import CloudFile
from core.models import ImageItem


class FetchWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, provider, url):
        super().__init__()
        self._provider = provider
        self._url = url

    def run(self):
        try:
            files = self._provider.list_files(self._url)
            self.finished.emit(files)
        except Exception as e:
            self.error.emit(str(e))


class DownloadWorker(QThread):
    progress = pyqtSignal(int, int)  # current, total
    file_done = pyqtSignal(object, str)  # CloudFile, local_path
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, provider, files, cache):
        super().__init__()
        self._provider = provider
        self._files = files
        self._cache = cache

    def run(self):
        total = len(self._files)
        for i, cf in enumerate(self._files):
            try:
                cached = self._cache.get(cf)
                if cached:
                    self.file_done.emit(cf, cached)
                else:
                    resp = requests.get(cf.download_url)
                    resp.raise_for_status()
                    path = self._cache.put(cf, resp.content)
                    self.file_done.emit(cf, path)
            except Exception:
                pass  # skip failed files
            self.progress.emit(i + 1, total)
        self.finished.emit()


class UrlDialog(QDialog):
    images_loaded = pyqtSignal(list)  # list of ImageItem

    def __init__(self, theme, timer=300, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Загрузка по URL")
        self.theme = theme
        self._timer = timer
        self._provider = None
        self._cloud_files = []
        self._cache = CacheManager()
        self._worker = None
        self._dl_worker = None

        self._build_ui()
        self._apply_theme()
        self.adjustSize()
        self.setMinimumWidth(400)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(8)

        # URL input row
        url_row = QHBoxLayout()
        url_row.setSpacing(6)
        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText("Вставьте ссылку Yandex Disk или Google Drive")
        self._url_input.returnPressed.connect(self._fetch)
        url_row.addWidget(self._url_input)
        self._fetch_btn = QPushButton("Загрузить")
        self._fetch_btn.clicked.connect(self._fetch)
        url_row.addWidget(self._fetch_btn)
        root.addLayout(url_row)

        # Status
        self._status = QLabel("")
        root.addWidget(self._status)

        # File list with checkboxes
        self._file_list = QListWidget()
        self._file_list.setIconSize(QSize(32, 32))
        self._file_list.setMinimumHeight(200)
        root.addWidget(self._file_list)

        # Select all / deselect all
        sel_row = QHBoxLayout()
        sel_row.setSpacing(6)
        self._sel_all_btn = QPushButton("Выбрать все")
        self._sel_all_btn.clicked.connect(self._select_all)
        sel_row.addWidget(self._sel_all_btn)
        self._sel_none_btn = QPushButton("Снять все")
        self._sel_none_btn.clicked.connect(self._select_none)
        sel_row.addWidget(self._sel_none_btn)
        sel_row.addStretch()
        self._count_label = QLabel("")
        sel_row.addWidget(self._count_label)
        root.addLayout(sel_row)

        # Progress bar
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        root.addWidget(self._progress)

        # Add button
        self._add_btn = QPushButton("Добавить")
        self._add_btn.clicked.connect(self._download_selected)
        self._add_btn.setEnabled(False)
        root.addWidget(self._add_btn)

        # Initially hide file list controls
        self._file_list.setVisible(False)
        self._sel_all_btn.setVisible(False)
        self._sel_none_btn.setVisible(False)
        self._count_label.setVisible(False)
        self._add_btn.setVisible(False)

    def _apply_theme(self):
        t = self.theme
        self.setStyleSheet(f"background-color: {t.bg}; color: {t.text_primary};")

        input_s = (f"background-color: {t.bg_secondary}; color: {t.text_primary}; "
                   f"border: 1px solid {t.border}; padding: 6px; font-size: 11px;")
        self._url_input.setStyleSheet(input_s)

        btn_s = (f"background-color: {t.bg_button}; color: {t.text_button}; "
                 f"border: 1px solid {t.border}; font-size: 10px; font-weight: 500; "
                 f"padding: 3px 6px;")
        for btn in [self._fetch_btn, self._sel_all_btn, self._sel_none_btn, self._add_btn]:
            btn.setStyleSheet(btn_s)

        self._status.setStyleSheet(
            f"color: {t.text_secondary}; font-size: 10px; font-weight: 500;")
        self._count_label.setStyleSheet(
            f"color: {t.text_secondary}; font-size: 10px; font-weight: 500;")

        list_s = (f"QListWidget {{ background-color: {t.bg_secondary}; border: none; "
                  f"font-size: 11px; color: {t.text_primary}; }}"
                  f"QListWidget::item {{ padding: 3px; }}"
                  f"QListWidget::item:selected {{ background-color: {t.bg_active}; }}")
        self._file_list.setStyleSheet(list_s)

        self._progress.setStyleSheet(
            f"QProgressBar {{ background-color: {t.bg_secondary}; border: 1px solid {t.border}; "
            f"height: 8px; }} "
            f"QProgressBar::chunk {{ background-color: {t.text_secondary}; }}")

    def _fetch(self):
        url = self._url_input.text().strip()
        if not url:
            return

        self._provider = detect_provider(url)
        if not self._provider:
            self._status.setText("Неизвестный сервис. Поддерживаются Yandex Disk и Google Drive")
            return

        self._status.setText("Загрузка списка файлов...")
        self._fetch_btn.setEnabled(False)
        self._file_list.clear()

        self._worker = FetchWorker(self._provider, url)
        self._worker.finished.connect(self._on_fetch_done)
        self._worker.error.connect(self._on_fetch_error)
        self._worker.start()

    def _on_fetch_done(self, files):
        self._cloud_files = files
        self._file_list.clear()
        self._fetch_btn.setEnabled(True)

        if not files:
            self._status.setText("Изображений не найдено")
            return

        for cf in files:
            item = QListWidgetItem(cf.name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            item.setData(Qt.ItemDataRole.UserRole, cf)
            self._file_list.addItem(item)

        self._status.setText(f"Найдено изображений: {len(files)}")
        self._file_list.setVisible(True)
        self._sel_all_btn.setVisible(True)
        self._sel_none_btn.setVisible(True)
        self._count_label.setVisible(True)
        self._add_btn.setVisible(True)
        self._add_btn.setEnabled(True)
        self._update_count()
        self._file_list.itemChanged.connect(self._update_count)
        self.adjustSize()

    def _on_fetch_error(self, msg):
        self._fetch_btn.setEnabled(True)
        if "404" in msg or "403" in msg:
            self._status.setText("Нет доступа. Убедитесь что ссылка публичная")
        else:
            self._status.setText("Ошибка сети. Проверьте подключение к интернету")

    def _select_all(self):
        for i in range(self._file_list.count()):
            self._file_list.item(i).setCheckState(Qt.CheckState.Checked)

    def _select_none(self):
        for i in range(self._file_list.count()):
            self._file_list.item(i).setCheckState(Qt.CheckState.Unchecked)

    def _update_count(self):
        checked = sum(1 for i in range(self._file_list.count())
                      if self._file_list.item(i).checkState() == Qt.CheckState.Checked)
        total = self._file_list.count()
        self._count_label.setText(f"{checked} / {total}")
        self._add_btn.setEnabled(checked > 0)

    def _get_selected_files(self):
        selected = []
        for i in range(self._file_list.count()):
            item = self._file_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected.append(item.data(Qt.ItemDataRole.UserRole))
        return selected

    def _download_selected(self):
        files = self._get_selected_files()
        if not files:
            return

        self._add_btn.setEnabled(False)
        self._fetch_btn.setEnabled(False)
        self._progress.setVisible(True)
        self._progress.setMaximum(len(files))
        self._progress.setValue(0)
        self._status.setText("Скачивание...")

        self._results = []
        url = self._url_input.text().strip()
        self._dl_worker = DownloadWorker(self._provider, files, self._cache)
        self._dl_worker.progress.connect(self._on_dl_progress)
        self._dl_worker.file_done.connect(self._on_file_done)
        self._dl_worker.finished.connect(self._on_dl_finished)
        self._dl_worker.start()

    def _on_dl_progress(self, current, total):
        self._progress.setValue(current)
        self._status.setText(f"Скачивание... {current}/{total}")

    def _on_file_done(self, cf, local_path):
        url_text = self._url_input.text().strip()
        img = ImageItem(path=local_path, timer=self._timer, source_url=url_text)
        self._results.append(img)

    def _on_dl_finished(self):
        self._progress.setVisible(False)
        if self._results:
            self.images_loaded.emit(self._results)
            self._status.setText(f"Добавлено: {len(self._results)}")
        else:
            self._status.setText("Не удалось скачать файлы")
        self._add_btn.setEnabled(True)
        self._fetch_btn.setEnabled(True)
```

- [ ] **Step 2: Run the app and verify UrlDialog opens without crash**

Run: `python -c "from ui.url_dialog import UrlDialog; print('OK')"`
Expected: `OK` (import check only — full UI needs QApplication)

- [ ] **Step 3: Commit**

```bash
git add ui/url_dialog.py
git commit -m "feat: add UrlDialog for loading images from cloud URLs"
```

---

### Task 7: Add "URL" button to ImageEditorWindow

**Files:**
- Modify: `ui/image_editor_window.py`

- [ ] **Step 1: Add URL button to toolbar**

In `ui/image_editor_window.py`, in the `_build_ui` method, after the `self._add_folder_btn` widget is added, insert:

```python
        self._url_btn = QPushButton("URL")
        self._url_btn.clicked.connect(self._add_from_url)
        toolbar.addWidget(self._url_btn)
```

- [ ] **Step 2: Add URL button to theme styling**

In `_apply_theme`, add `self._url_btn` to the button list:

```python
        for btn in [self._add_files_btn, self._add_folder_btn, self._url_btn,
                    self._clear_btn, self._del_btn, self._up_btn, self._down_btn]:
```

- [ ] **Step 3: Add _add_from_url method**

Add after the `_add_folder` method:

```python
    def _add_from_url(self):
        from ui.url_dialog import UrlDialog
        timer = 300
        if self._parent and hasattr(self._parent, "get_timer_seconds"):
            timer = self._parent.get_timer_seconds()
        dlg = UrlDialog(self.theme, timer=timer, parent=self)
        dlg.images_loaded.connect(self._on_url_images)
        dlg.exec()

    def _on_url_images(self, images):
        for img in images:
            self.images.append(img)
        self._pix_cache.clear()
        self._rebuild()
        self._emit()
```

- [ ] **Step 4: Test manually**

Run: `python main.py`
1. Open image editor
2. Click "URL"
3. Verify dialog opens with correct styling
4. Paste a Yandex Disk public link
5. Verify file list appears
6. Select/deselect files
7. Click "Добавить" — files appear in editor

- [ ] **Step 5: Commit**

```bash
git add ui/image_editor_window.py
git commit -m "feat: add URL button to image editor for cloud loading"
```

---

### Task 8: Add "Очистить кеш" button to settings

**Files:**
- Modify: `ui/settings_window.py`

- [ ] **Step 1: Add cache clear button**

In `ui/settings_window.py`, in `_build_ui`, after the `self._topmost_cb` widget (section `# 8. Always-on-top checkbox`), add:

```python
        # 8.5. Cache clear button
        cache_row = QHBoxLayout()
        cache_row.addStretch()
        self._cache_btn = QPushButton("Очистить кеш")
        self._cache_btn.clicked.connect(self._clear_cache)
        cache_row.addWidget(self._cache_btn)
        self._cache_size_label = QLabel("")
        cache_row.addWidget(self._cache_size_label)
        cache_row.addStretch()
        root.addWidget(self._topmost_cb)  # move existing line here if needed
        root.addLayout(cache_row)
```

Note: keep existing `root.addWidget(self._topmost_cb)` in its place. Add the `cache_row` layout right after it:

```python
        root.addLayout(cache_row)
```

- [ ] **Step 2: Add import and methods**

At the top of `ui/settings_window.py`, add to imports:

```python
from core.cloud.cache import CacheManager
```

Add methods:

```python
    def _clear_cache(self):
        cm = CacheManager()
        cm.clear()
        self._update_cache_size()

    def _update_cache_size(self):
        cm = CacheManager()
        size = cm.size()
        if size > 0:
            self._cache_size_label.setText(CacheManager.format_size(size))
        else:
            self._cache_size_label.setText("")
```

- [ ] **Step 3: Style the cache button and label**

In `_apply_theme`, add styling for the cache button (use same style as `auto_s`):

```python
        self._cache_btn.setStyleSheet(auto_s)
        self._cache_size_label.setStyleSheet(
            f"color: {t.text_secondary}; font-size: 10px; font-weight: 500;")
```

- [ ] **Step 4: Call _update_cache_size on init**

At the end of `_restore_session`, add:

```python
        self._update_cache_size()
```

- [ ] **Step 5: Test manually**

Run: `python main.py`
1. Verify "Очистить кеш" button appears below "Поверх всех окон"
2. Load some images via URL
3. Verify cache size appears
4. Click "Очистить кеш"
5. Verify size goes away

- [ ] **Step 6: Commit**

```bash
git add ui/settings_window.py
git commit -m "feat: add cache clear button to settings window"
```

---

### Task 9: Run all tests and verify

**Files:** none (verification only)

- [ ] **Step 1: Run full test suite**

Run: `python -m pytest tests/ -v`
Expected: all tests PASS, no regressions

- [ ] **Step 2: Run the app end-to-end**

Run: `python main.py`
Manual checklist:
1. App starts normally
2. Existing images load from session
3. Image editor opens, "URL" button visible
4. Click URL — dialog opens
5. Paste Yandex Disk link — files listed with checkboxes
6. Select some, click "Добавить" — images appear in editor with correct timer
7. Close and reopen app — cloud images still visible (from cache)
8. "Очистить кеш" works
9. Light/dark theme applies to all new UI elements

- [ ] **Step 3: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix: polish cloud image loading"
```
