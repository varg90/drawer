import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import tempfile
from main import (
    validate_timer_seconds, filter_image_files, save_session, load_session,
    format_time, auto_warn_seconds, SUPPORTED_FORMATS, TIMER_PRESETS,
    TIMER_MIN, TIMER_MAX, SESSION_FILE,
)


# --- Constants ---

def test_supported_formats():
    assert ".jpg" in SUPPORTED_FORMATS
    assert ".jpeg" in SUPPORTED_FORMATS
    assert ".png" in SUPPORTED_FORMATS
    assert ".gif" in SUPPORTED_FORMATS
    assert ".bmp" in SUPPORTED_FORMATS
    assert ".webp" in SUPPORTED_FORMATS
    assert ".txt" not in SUPPORTED_FORMATS


def test_timer_presets():
    assert len(TIMER_PRESETS) == 6
    seconds_values = [s for s, _ in TIMER_PRESETS]
    assert seconds_values == [60, 300, 600, 900, 1800, 3600]
    # All labels are strings
    for _, label in TIMER_PRESETS:
        assert isinstance(label, str)


def test_timer_range():
    assert TIMER_MIN == 1
    assert TIMER_MAX == 10800  # 3 hours


def test_session_file_path():
    assert SESSION_FILE.endswith("session.json")


# --- format_time ---

def test_format_time_seconds():
    assert format_time(0) == "0:00"
    assert format_time(1) == "0:01"
    assert format_time(9) == "0:09"
    assert format_time(30) == "0:30"
    assert format_time(59) == "0:59"


def test_format_time_minutes():
    assert format_time(60) == "1:00"
    assert format_time(61) == "1:01"
    assert format_time(90) == "1:30"
    assert format_time(600) == "10:00"
    assert format_time(3599) == "59:59"


def test_format_time_hours():
    assert format_time(3600) == "1:00:00"
    assert format_time(3661) == "1:01:01"
    assert format_time(7200) == "2:00:00"
    assert format_time(10800) == "3:00:00"


# --- validate_timer_seconds ---

def test_validate_timer_valid():
    assert validate_timer_seconds(1) == 1
    assert validate_timer_seconds(60) == 60
    assert validate_timer_seconds(300) == 300
    assert validate_timer_seconds(10800) == 10800


def test_validate_timer_clamps_low():
    assert validate_timer_seconds(0) == 1
    assert validate_timer_seconds(-5) == 1
    assert validate_timer_seconds(-100) == 1


def test_validate_timer_clamps_high():
    assert validate_timer_seconds(10801) == 10800
    assert validate_timer_seconds(99999) == 10800
    assert validate_timer_seconds(1000000) == 10800


def test_validate_timer_float():
    assert validate_timer_seconds(5.7) == 5
    assert validate_timer_seconds(59.9) == 59


def test_validate_timer_boundary():
    assert validate_timer_seconds(1) == 1
    assert validate_timer_seconds(10800) == 10800


# --- filter_image_files ---

def test_filter_image_files_mixed():
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


def test_filter_image_files_all_images():
    files = ["a.jpg", "b.png", "c.gif"]
    assert filter_image_files(files) == files


def test_filter_image_files_case_insensitive():
    files = ["A.JPG", "B.Png", "C.GIF", "D.WeBp"]
    assert filter_image_files(files) == files


def test_filter_image_files_with_paths():
    files = [
        "C:/photos/vacation/beach.jpg",
        "C:/docs/report.pdf",
        "/home/user/art.webp",
    ]
    result = filter_image_files(files)
    assert result == ["C:/photos/vacation/beach.jpg", "/home/user/art.webp"]


def test_filter_image_files_dotfiles():
    files = [".hidden.jpg", ".gitignore", "normal.png"]
    result = filter_image_files(files)
    assert result == [".hidden.jpg", "normal.png"]


def test_filter_image_files_no_extension():
    files = ["README", "Makefile", "photo"]
    assert filter_image_files(files) == []


def test_filter_image_files_double_extension():
    files = ["archive.tar.gz", "photo.backup.jpg", "doc.txt.png"]
    result = filter_image_files(files)
    assert result == ["photo.backup.jpg", "doc.txt.png"]


# --- save_session / load_session ---

def test_save_and_load_session():
    data = {
        "images": [{"path": "C:/photos/a.jpg", "timer": 60}],
        "timer_mode": "uniform",
        "uniform_timer": 300,
        "order": "sequential",
        "always_on_top": True,
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


def test_save_session_unicode():
    data = {"name": "Оксана", "path": "C:/фото/картинка.jpg"}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        path = f.name
    save_session(data, path)
    loaded = load_session(path)
    assert loaded == data
    os.unlink(path)


def test_save_session_empty():
    data = {}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        path = f.name
    save_session(data, path)
    loaded = load_session(path)
    assert loaded == data
    os.unlink(path)


def test_save_session_overwrites():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        path = f.name
    save_session({"v": 1}, path)
    save_session({"v": 2}, path)
    loaded = load_session(path)
    assert loaded == {"v": 2}
    os.unlink(path)


def test_load_session_empty_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        path = f.name
    result = load_session(path)
    assert result is None
    os.unlink(path)


def test_save_session_large_image_list():
    data = {
        "images": [{"path": f"C:/img/{i}.jpg", "timer": 60} for i in range(1000)]
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        path = f.name
    save_session(data, path)
    loaded = load_session(path)
    assert len(loaded["images"]) == 1000
    os.unlink(path)


# --- auto_warn_seconds ---

def test_auto_warn_up_to_2min():
    assert auto_warn_seconds(1) == 10
    assert auto_warn_seconds(30) == 10
    assert auto_warn_seconds(60) == 10
    assert auto_warn_seconds(120) == 10


def test_auto_warn_2min_to_5min():
    assert auto_warn_seconds(121) == 30
    assert auto_warn_seconds(180) == 30
    assert auto_warn_seconds(300) == 30


def test_auto_warn_5min_to_15min():
    assert auto_warn_seconds(301) == 60
    assert auto_warn_seconds(600) == 60
    assert auto_warn_seconds(900) == 60


def test_auto_warn_15min_to_1hour():
    assert auto_warn_seconds(901) == 300
    assert auto_warn_seconds(1800) == 300
    assert auto_warn_seconds(3600) == 300


def test_auto_warn_1hour_to_3hours():
    assert auto_warn_seconds(3601) == 600
    assert auto_warn_seconds(7200) == 600
    assert auto_warn_seconds(10800) == 600


def test_auto_warn_boundaries():
    # Exact boundary values
    assert auto_warn_seconds(120) == 10    # 2 min exactly -> up to 2 min
    assert auto_warn_seconds(121) == 30    # 2:01 -> next tier
    assert auto_warn_seconds(300) == 30    # 5 min exactly
    assert auto_warn_seconds(301) == 60    # 5:01
    assert auto_warn_seconds(900) == 60    # 15 min exactly
    assert auto_warn_seconds(901) == 300   # 15:01
    assert auto_warn_seconds(3600) == 300  # 1 hour exactly
    assert auto_warn_seconds(3601) == 600  # 1:00:01
