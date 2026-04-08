import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import Qt, pyqtSignal, QSize
import qtawesome as qta
from ui.editor_panel import EditorPanel
from ui.icons import Icons
from ui.scales import S
from ui.widgets import make_icon_btn


class ImageEditorWindow(QWidget):
    """Detached editor window — thin wrapper around EditorPanel."""
    images_updated = pyqtSignal(list)

    def __init__(self, images, theme, parent=None, view_mode="list"):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.images = list(images)
        self.theme = theme
        self._parent = parent
        self.__dict__['_view_mode_init'] = view_mode if view_mode in ("list", "grid") else "list"
        self._build_ui()
        self._apply_theme()

        self.adjustSize()
        if parent is not None:
            pg = parent.geometry()
            x = pg.x() + (pg.width() - self.width()) // 2
            y = pg.y() + (pg.height() - self.height()) // 2
            self.move(x, y)

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
        self._dock_btn = QPushButton()
        self._dock_btn.setIcon(qta.icon(Icons.DOCK, color=self.theme.text_button))
        self._dock_btn.setIconSize(QSize(12, 12))
        self._dock_btn.setFixedSize(22, 20)
        self._dock_btn.setToolTip("Dock to main window")
        self._dock_btn.setStyleSheet(
            f"background-color: {self.theme.bg_button}; "
            f"border: 1px solid {self.theme.border};")
        self._dock_btn.clicked.connect(self._on_dock_back)
        title_bar.addWidget(self._dock_btn)
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
        # Drag handle is only useful when docked; hide it in the float window
        self._panel._drag_handle.hide()
        root.addWidget(self._panel)

    def _apply_theme(self):
        self.setStyleSheet(f"background-color: {self.theme.bg};")

    def _on_panel_update(self, images):
        self.images = images
        self.images_updated.emit(images)

    def _on_dock_back(self):
        if self._parent and hasattr(self._parent, '_dock_editor_from_detached'):
            self._parent._dock_editor_from_detached(self.images, self._panel._view_mode)
        self.close()

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
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and hasattr(self, '_drag_pos'):
            new_pos = event.globalPosition().toPoint() - self._drag_pos
            self.move(new_pos)
            # Check proximity to main window for snap-to-dock
            if self._parent and self._parent.isVisible():
                self._check_dock_snap(new_pos)
            event.accept()

    def _check_dock_snap(self, pos):
        """Dock back to main window if floating editor drifts close enough."""
        main_geo = self._parent.geometry()
        snap_distance = 20

        # Right-edge snap: editor's left aligns with main window's right edge
        editor_top = pos.y()
        vertical_overlap = (
            editor_top < main_geo.bottom() + snap_distance
            and editor_top + self.height() > main_geo.top() - snap_distance
        )
        if abs(pos.x() - main_geo.right()) < snap_distance and vertical_overlap:
            self._do_dock()
            return

        # Bottom-edge snap: editor's top aligns with main window's bottom edge
        if (abs(editor_top - main_geo.bottom()) < snap_distance
                and abs(pos.x() - main_geo.left()) < snap_distance):
            self._do_dock()

    def _do_dock(self):
        """Ask the main window to re-dock this editor, then close the float."""
        if self._parent and hasattr(self._parent, '_dock_editor_from_detached'):
            view = self._panel._view_mode if hasattr(self, '_panel') else 'list'
            self._parent._dock_editor_from_detached(self.images, view)
        self.close()

    def mouseReleaseEvent(self, event):
        if hasattr(self, '_drag_pos'):
            del self._drag_pos

    def closeEvent(self, event):
        if self._parent and hasattr(self._parent, '_on_editor_close'):
            self._parent._on_editor_close()
        super().closeEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            self._panel._delete_selected()
        else:
            super().keyPressEvent(event)
