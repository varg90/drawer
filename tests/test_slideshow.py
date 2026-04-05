import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from main import validate_timer_seconds, filter_image_files


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
