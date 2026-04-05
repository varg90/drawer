import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import tempfile
from main import validate_timer_seconds, filter_image_files, save_session, load_session


def test_import():
    import main
    assert hasattr(main, "SUPPORTED_FORMATS")


def test_validate_timer_valid():
    assert validate_timer_seconds(1) == 1
    assert validate_timer_seconds(60) == 60
    assert validate_timer_seconds(10800) == 10800


def test_validate_timer_clamps():
    assert validate_timer_seconds(0) == 1
    assert validate_timer_seconds(-5) == 1
    assert validate_timer_seconds(99999) == 10800


def test_filter_image_files():
    files = [
        "photo.jpg",
        "image.PNG",
        "doc.txt",
        "art.webp",
        "data.csv",
        "pic.gif",
        "shot.bmp",
        "render.jpeg",
    ]
    result = filter_image_files(files)
    assert result == ["photo.jpg", "image.PNG", "art.webp", "pic.gif", "shot.bmp", "render.jpeg"]


def test_filter_image_files_empty():
    assert filter_image_files([]) == []
    assert filter_image_files(["readme.txt", "data.csv"]) == []


def test_save_and_load_session():
    data = {
        "images": [{"path": "C:/photos/a.jpg", "timer": 60}],
        "timer_mode": "uniform",
        "uniform_timer": 300,
        "order": "sequential",
        "always_on_top": True,
        "loop": True,
        "fit_window": True,
        "lock_aspect": False,
        "window_x": 100,
        "window_y": 200,
        "window_w": 800,
        "window_h": 600,
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        path = f.name

    save_session(data, path)
    loaded = load_session(path)
    assert loaded == data
    os.unlink(path)


def test_load_session_missing_file():
    result = load_session("nonexistent_file_12345.json")
    assert result is None


def test_load_session_corrupted():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("not valid json{{{")
        path = f.name
    result = load_session(path)
    assert result is None
    os.unlink(path)
