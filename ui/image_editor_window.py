import os
import weakref
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QLinearGradient
import qtawesome as qta
from ui.editor_panel import EditorPanel
from ui.icons import Icons
from ui.scales import S
from ui.widgets import make_icon_btn
from ui.snap import SnapMixin
from ui.rounded_window import RoundedWindowMixin


class ImageEditorWindow(QWidget, SnapMixin, RoundedWindowMixin):
    """Editor window — always a separate window with magnetic snap."""
    images_updated = pyqtSignal(list)

    shuffle_changed = pyqtSignal(bool)

    def __init__(self, images, theme, parent=None, view_mode="list", shuffle=True):
        QWidget.__init__(self, parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.images = list(images)
        self.theme = theme
        self._parent_ref = weakref.ref(parent) if parent else lambda: None
        self.__dict__['_view_mode_init'] = view_mode if view_mode in ("list", "grid") else "list"
        self._shuffle_init = shuffle
        self.setMinimumSize(S.EDITOR_MIN_W, S.EDITOR_MIN_H)
        self._resizing = False
        self._resize_edge = None
        self._resize_start = None
        self._resize_geo = None
        self._last_edge = None
        self._build_ui()
        self._apply_theme()
        SnapMixin.__init__(self)
        self.rounded_init()
        self.setMouseTracking(True)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(S.MARGIN, S.MARGIN_TOP, S.MARGIN, S.MARGIN_BOTTOM)
        root.setSpacing(0)

        # Title bar — add buttons left, close/minimize right
        title_bar = QHBoxLayout()
        title_bar.setContentsMargins(0, 0, 0, 0)
        title_bar.setSpacing(S.EDITOR_TITLE_SPACING)

        self._add_files_btn = make_icon_btn(Icons.ADD_FILE, self.theme.text_hint,
                                             size=S.ICON_HEADER, tooltip="Add files")
        self._add_folder_btn = make_icon_btn(Icons.ADD_FOLDER, self.theme.text_hint,
                                              size=S.ICON_HEADER, tooltip="Add folder")
        self._add_url_btn = make_icon_btn(Icons.ADD_URL, self.theme.text_hint,
                                           size=S.ICON_HEADER, tooltip="Load from URL")

        title_bar.addWidget(self._add_files_btn)
        title_bar.addWidget(self._add_folder_btn)
        title_bar.addWidget(self._add_url_btn)
        title_bar.addStretch()
        self._close_btn = make_icon_btn(Icons.CLOSE, self.theme.text_hint,
                                        size=S.ICON_HEADER)
        self._close_btn.clicked.connect(self.close)
        title_bar.addWidget(self._close_btn)
        root.addLayout(title_bar)
        root.addSpacing(S.EDITOR_TITLE_BOTTOM_SPACE)

        # Editor panel
        init_view = self.__dict__.get('_view_mode_init', 'list')
        self._panel = EditorPanel(
            self.images, self.theme, parent=self, view_mode=init_view,
            shuffle=self._shuffle_init)
        self._panel.images_updated.connect(self._on_panel_update)
        self._panel.shuffle_changed.connect(self.shuffle_changed.emit)
        self._panel.close_requested.connect(self.close)
        # Connect title bar add buttons to panel methods
        self._add_files_btn.clicked.connect(self._panel._add_files)
        self._add_folder_btn.clicked.connect(self._panel._add_folder)
        self._add_url_btn.clicked.connect(self._panel._add_from_url)

        root.addWidget(self._panel)

    def _apply_theme(self):
        t = self.theme
        self.setStyleSheet("background-color: transparent; font-family: 'Lexend';")
        self.update()
        self._add_files_btn.setIcon(qta.icon(Icons.ADD_FILE, color=t.text_hint))
        self._add_folder_btn.setIcon(qta.icon(Icons.ADD_FOLDER, color=t.text_hint))
        self._add_url_btn.setIcon(qta.icon(Icons.ADD_URL, color=t.text_hint))
        self._close_btn.setIcon(qta.icon(Icons.CLOSE, color=t.text_hint))

    # ------------------------------------------------------------------ Rounded painting

    def corner_radii(self):
        r = S.WINDOW_RADIUS
        # When snapped to main window (on its right side), round right corners only
        if self._snapped_to is not None:
            return (0, r, r, 0)
        return (r, r, r, r)

    def _bg_color(self):
        return QColor(self.theme.bg_secondary)

    def _border_color(self):
        return QColor(self.theme.border)

    def _bg_brush(self):
        return QColor(self.theme.bg_secondary)

    def paintEvent(self, event):
        self._paint_rounded(event)
        # Don't call super — we handle all painting

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

    def _edge_at(self, pos):
        """Return which edge(s) the cursor is near, or None."""
        r = self.rect()
        e = S.RESIZE_GRIP_W
        edges = ""
        if pos.y() < e:
            edges += "t"
        elif pos.y() > r.height() - e:
            edges += "b"
        if pos.x() < e:
            edges += "l"
        elif pos.x() > r.width() - e:
            edges += "r"
        return edges or None

    def _cursor_for_edge(self, edge):
        if edge in ("t", "b"):
            return Qt.CursorShape.SizeVerCursor
        if edge in ("l", "r"):
            return Qt.CursorShape.SizeHorCursor
        if edge in ("tl", "br"):
            return Qt.CursorShape.SizeFDiagCursor
        if edge in ("tr", "bl"):
            return Qt.CursorShape.SizeBDiagCursor
        return Qt.CursorShape.ArrowCursor

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            edge = self._edge_at(event.pos())
            if edge:
                self._resizing = True
                self._resize_edge = edge
                self._resize_start = event.globalPosition().toPoint()
                self._resize_geo = self.geometry()
                event.accept()
                return
        self._resizing = False
        self.snap_mouse_press(event)

    def mouseMoveEvent(self, event):
        # Update cursor on hover — only call setCursor when edge changes
        if not event.buttons():
            edge = self._edge_at(event.pos())
            if edge != self._last_edge:
                self._last_edge = edge
                self.setCursor(self._cursor_for_edge(edge) if edge else Qt.CursorShape.ArrowCursor)
            return

        # Resize
        if self._resizing and self._resize_edge:
            delta = event.globalPosition().toPoint() - self._resize_start
            geo = self._resize_geo
            from PyQt6.QtCore import QRect
            new_geo = QRect(geo)
            e = self._resize_edge
            if "r" in e:
                new_geo.setRight(geo.right() + delta.x())
            if "b" in e:
                new_geo.setBottom(geo.bottom() + delta.y())
            if "l" in e:
                new_geo.setLeft(geo.left() + delta.x())
            if "t" in e:
                new_geo.setTop(geo.top() + delta.y())
            if new_geo.width() >= self.minimumWidth() and new_geo.height() >= self.minimumHeight():
                # Snap edges to parent window during resize
                p = self._parent_ref()
                if p:
                    pg = p.geometry()
                    snap = S.EDGE_SNAP_THRESHOLD
                    if "b" in e and abs(new_geo.bottom() - pg.bottom()) < snap:
                        new_geo.setBottom(pg.bottom())
                    if "t" in e and abs(new_geo.top() - pg.top()) < snap:
                        new_geo.setTop(pg.top())
                    if "r" in e and abs(new_geo.right() - pg.right()) < snap:
                        new_geo.setRight(pg.right())
                    if "l" in e and abs(new_geo.left() - pg.left()) < snap:
                        new_geo.setLeft(pg.left())
                self.setGeometry(new_geo)
            event.accept()
            return

        self.snap_mouse_move(event)

    def _on_snapped(self, other, side):
        """Reset size to match parent when re-snapping."""
        self.resize(S.EDITOR_W, other.height())

    def mouseReleaseEvent(self, event):
        self._resizing = False
        self._resize_edge = None
        self.snap_mouse_release(event)

    def closeEvent(self, event):
        self.snap_cleanup()
        p = self._parent_ref()
        if p and hasattr(p, '_on_editor_close'):
            p._on_editor_close()
        super().closeEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            self._panel._delete_selected()
        else:
            super().keyPressEvent(event)
