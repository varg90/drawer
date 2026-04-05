import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import tempfile
from core.session import save_session, load_session

def test_save_and_load():
    data = {"images": [{"path": "C:/a.jpg", "timer": 60}], "order": "sequential"}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        path = f.name
    save_session(data, path)
    assert load_session(path) == data
    os.unlink(path)

def test_load_missing():
    assert load_session("nonexistent_12345.json") is None

def test_load_corrupted():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("not json{{{")
        path = f.name
    assert load_session(path) is None
    os.unlink(path)

def test_save_unicode():
    data = {"name": "Оксана"}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        path = f.name
    save_session(data, path)
    assert load_session(path) == data
    os.unlink(path)

def test_save_empty():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        path = f.name
    save_session({}, path)
    assert load_session(path) == {}
    os.unlink(path)

def test_save_overwrites():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        path = f.name
    save_session({"v": 1}, path)
    save_session({"v": 2}, path)
    assert load_session(path) == {"v": 2}
    os.unlink(path)

def test_load_empty_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        path = f.name
    assert load_session(path) is None
    os.unlink(path)

def test_save_large_list():
    data = {"images": [{"path": f"C:/img/{i}.jpg", "timer": 60} for i in range(1000)]}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        path = f.name
    save_session(data, path)
    assert len(load_session(path)["images"]) == 1000
    os.unlink(path)
