import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.file_utils import filter_image_files

def test_filter_mixed():
    files = ["photo.jpg", "image.PNG", "doc.txt", "art.webp", "data.csv", "pic.gif", "shot.bmp", "render.jpeg"]
    result = filter_image_files(files)
    assert result == ["photo.jpg", "image.PNG", "art.webp", "pic.gif", "shot.bmp", "render.jpeg"]

def test_filter_empty():
    assert filter_image_files([]) == []
    assert filter_image_files(["readme.txt"]) == []

def test_filter_all_images():
    assert filter_image_files(["a.jpg", "b.png"]) == ["a.jpg", "b.png"]

def test_filter_case_insensitive():
    assert filter_image_files(["A.JPG", "B.Png"]) == ["A.JPG", "B.Png"]

def test_filter_with_paths():
    files = ["C:/photos/beach.jpg", "C:/docs/report.pdf", "/home/user/art.webp"]
    assert filter_image_files(files) == ["C:/photos/beach.jpg", "/home/user/art.webp"]

def test_filter_no_extension():
    assert filter_image_files(["README", "Makefile"]) == []

def test_filter_double_extension():
    assert filter_image_files(["photo.backup.jpg", "doc.txt.png"]) == ["photo.backup.jpg", "doc.txt.png"]
