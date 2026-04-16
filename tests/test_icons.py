# tests/test_icons.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ui.icons import Icons


def test_start_icon():
    assert Icons.START == "fa6s.pencil"


def test_topmost_toggle():
    assert Icons.TOPMOST_ON == "ph.push-pin-fill"
    assert Icons.TOPMOST_OFF == "ph.push-pin-bold"


def test_theme_toggle():
    assert Icons.THEME_DARK == "ph.moon-bold"
    assert Icons.THEME_LIGHT == "ph.sun-bold"


def test_editor_icons():
    assert Icons.ADD_FILE == "ph.file-plus-bold"
    assert Icons.ADD_FOLDER == "ph.folder-plus-bold"
    assert Icons.ERASER == "ph.eraser-bold"
    assert Icons.CLOSE == "ph.x-bold"
    assert Icons.DETACH == "ph.arrow-square-out-bold"
    assert Icons.DOCK == "ph.arrows-in-bold"
    assert Icons.INFO == "ph.info-bold"
    assert Icons.PLUS == "ph.image-square-fill"
