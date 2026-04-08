import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import Qt, pyqtSignal, QSize
import qtawesome as qta
from ui.editor_panel import EditorPanel
from ui.icons import Icons
from ui.scales import S
from ui.widgets import make_icon_btn
from ui.snap import SnapMixin


class ImageEditorWindow(QWidget, SnapMixin):
    """Editor window — always a separate window with magnetic snap."""
    images_updated = pyqtSignal(list)

    def __init__(self, images, theme, parent=None, view_mode="list"):
        QWidget.__init__(self)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.images = list(images)
        self.theme = theme
        self._parent = parent
        self.__dict__['_view_mode_init'] = view_mode if view_mode in ("list", "grid") else "list"
        self._build_ui()
        self._apply_theme()
        SnapMixin.__init__(self)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Title bar with dock-back button
        title_bar = QHBoxLayout()
        title_bar.setContentsMargins(8, 5, 8, 3)
        title_bar.setSpacing(4)
        title = QLabel("Images")
        title.setStyleSheet(
            f"color: {self.theme.text_secondary}; "
            f"font-size: {S.FONT_BUTTON}px; font-weight: 500;")
        title_bar.addWidget(title)
        title_bar.addStretch()
        self._min_btn = make_icon_btn(Icons.MINIMIZE, self.theme.text_hint)
        self._min_btn.clicked.connect(self.showMinimized)
        title_bar.addWidget(self._min_btn)
        self._close_btn = make_icon_btn(Icons.CLOSE, self.theme.text_hint)
        self._close_btn.clicked.connect(self.close)
        title_bar.addWidget(self._close_btn)
        root.addLayout(title_bar)

        # Editor panel
        init_view = self.__dict__.get('_view_mode_init', 'list')
        self._panel = EditorPanel(
            self.images, self.theme, parent=self, view_mode=init_view)
        self._panel.images_updated.connect(self._on_panel_update)
        self._panel.close_requested.connect(self.close)
        # Hide the detach button — already detached
        self._panel._detach_btn.setVisible(False)
        root.addWidget(self._panel)

    def _apply_theme(self):
        self.setStyleSheet(f"background-color: {self.theme.bg};")

    def _on_panel_update(self, images):
        self.images = images
        self.images_updated.emit(images)

    def refresh(self, images):
        self.images = list(images)
        self._panel.refresh(images)

    @property
    def _view_mode(self):
        if hasattr(self, '_panel'):
            return self._panel._view_mode
        return self.__dict__.get('_view_mode_init', 'list')

    @_view_mode.setter
    def _view_mode(self, val):
        self.__dict__['_view_mode_init'] = val

    def mousePressEvent(self, event):
        self.snap_mouse_press(event)

    def mouseMoveEvent(self, event):
        self.snap_mouse_move(event)

    def mouseReleaseEvent(self, event):
        self.snap_mouse_release(event)

    def closeEvent(self, event):
        self.snap_cleanup()
        if self._parent and hasattr(self._parent, '_on_editor_close'):
            self._parent._on_editor_close()
        super().closeEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            self._panel._delete_selected()
        else:
            super().keyPressEvent(event)
