import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ui.editor_panel import EditorPanel


def test_editor_panel_exists():
    assert EditorPanel is not None


def test_editor_panel_is_widget():
    from PyQt6.QtWidgets import QWidget
    assert issubclass(EditorPanel, QWidget)
