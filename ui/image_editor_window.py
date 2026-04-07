import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QLabel, QListWidget, QListWidgetItem, QFileDialog,
                              QSlider, QStackedWidget)
from PyQt6.QtGui import QPixmap, QIcon, QColor, QBrush
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from core.constants import SUPPORTED_FORMATS
from core.file_utils import filter_image_files, scan_folder
from core.models import ImageItem
from core.timer_logic import format_time
from core.cloud.cache import CacheManager

GRID_MIN = 48
GRID_MAX = 200
GRID_DEFAULT = 80


class ImageEditorWindow(QWidget):
    images_updated = pyqtSignal(list)

    def __init__(self, images, theme, parent=None, view_mode="list"):
        super().__init__()
        self.images = list(images)
        self.theme = theme
        self._parent = parent
        self._view_mode = view_mode if view_mode in ("list", "grid") else "list"
        self._pix_cache = {}  # path -> QPixmap (original size, max ~GRID_MAX)
        self.setWindowTitle("Изображения")
        self._build_ui()
        self._set_view_mode(self._view_mode)
        self._apply_theme()
        self._rebuild()

        # Open at minimum size, centered over parent
        self.adjustSize()
        if parent is not None:
            pg = parent.geometry()
            x = pg.x() + (pg.width() - self.width()) // 2
            y = pg.y() + (pg.height() - self.height()) // 2
            self.move(x, y)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(8)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)
        self._add_files_btn = QPushButton("+ Файлы")
        self._add_files_btn.clicked.connect(self._add_files)
        toolbar.addWidget(self._add_files_btn)
        self._add_folder_btn = QPushButton("+ Папка")
        self._add_folder_btn.clicked.connect(self._add_folder)
        toolbar.addWidget(self._add_folder_btn)
        self._url_btn = QPushButton("URL")
        self._url_btn.clicked.connect(self._add_from_url)
        toolbar.addWidget(self._url_btn)
        toolbar.addStretch()
        self._del_btn = QPushButton("x")
        self._del_btn.setFixedSize(22, 22)
        self._del_btn.clicked.connect(self._delete_selected)
        toolbar.addWidget(self._del_btn)
        self._clear_btn = QPushButton("Очистить")
        self._clear_btn.clicked.connect(self._clear)
        toolbar.addWidget(self._clear_btn)
        root.addLayout(toolbar)

        # Count label — separate row
        self._count_label = QLabel("")
        root.addWidget(self._count_label)

        # Stacked widget: list view and grid view
        self._stack = QStackedWidget()

        # --- List view ---
        self._list = QListWidget()
        self._list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self._list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self._list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self._list.setIconSize(QSize(24, 24))
        self._list.model().rowsMoved.connect(self._on_reorder)
        self._stack.addWidget(self._list)

        # --- Grid view ---
        self._grid = QListWidget()
        self._grid.setViewMode(QListWidget.ViewMode.IconMode)
        self._grid.setResizeMode(QListWidget.ResizeMode.Adjust)
        self._grid.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self._grid.setDefaultDropAction(Qt.DropAction.MoveAction)
        self._grid.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self._grid.setMovement(QListWidget.Movement.Snap)
        self._grid.setSpacing(4)
        self._grid.setIconSize(QSize(GRID_DEFAULT, GRID_DEFAULT))
        self._grid.setGridSize(QSize(GRID_DEFAULT + 8, GRID_DEFAULT + 28))
        self._grid.model().rowsMoved.connect(self._on_grid_reorder)
        self._stack.addWidget(self._grid)

        root.addWidget(self._stack)

        # Bottom controls
        bottom = QHBoxLayout()
        bottom.setSpacing(6)

        # Up/down (list mode)
        self._up_btn = QPushButton("^")
        self._up_btn.setFixedSize(26, 22)
        self._up_btn.clicked.connect(self._move_up)
        bottom.addWidget(self._up_btn)
        self._down_btn = QPushButton("v")
        self._down_btn.setFixedSize(26, 22)
        self._down_btn.clicked.connect(self._move_down)
        bottom.addWidget(self._down_btn)

        # Zoom slider (grid mode)
        self._zoom_label = QLabel("Размер:")
        bottom.addWidget(self._zoom_label)
        self._zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self._zoom_slider.setRange(GRID_MIN, GRID_MAX)
        self._zoom_slider.setValue(GRID_DEFAULT)
        self._zoom_slider.setFixedWidth(100)
        self._zoom_slider.valueChanged.connect(self._on_zoom)
        bottom.addWidget(self._zoom_slider)

        # Cache clear
        self._cache_btn = QPushButton("Очистить кеш")
        self._cache_btn.clicked.connect(self._clear_cache)
        bottom.addWidget(self._cache_btn)
        self._cache_size_label = QLabel("")
        bottom.addWidget(self._cache_size_label)

        bottom.addStretch()

        # View mode toggle (always visible)
        self._list_btn = QPushButton("=")
        self._list_btn.setFixedSize(22, 22)
        self._list_btn.setToolTip("Список")
        self._list_btn.clicked.connect(lambda: self._set_view_mode("list"))
        bottom.addWidget(self._list_btn)
        self._grid_btn = QPushButton("#")
        self._grid_btn.setFixedSize(22, 22)
        self._grid_btn.setToolTip("Плитка")
        self._grid_btn.clicked.connect(lambda: self._set_view_mode("grid"))
        bottom.addWidget(self._grid_btn)

        root.addLayout(bottom)
        self._update_bottom_controls()

    def _apply_theme(self):
        t = self.theme
        self.setStyleSheet(f"background-color: {t.bg}; color: {t.text_primary};")

        self._count_label.setStyleSheet(
            f"color: {t.text_secondary}; font-size: 10px; font-weight: 500; "
            f"letter-spacing: 2px;")

        btn_s = (f"background-color: {t.bg_button}; color: {t.text_button}; "
                 f"border: 1px solid {t.border}; font-size: 10px; font-weight: 500; "
                 f"padding: 3px 6px;")
        for btn in [self._add_files_btn, self._add_folder_btn, self._url_btn,
                    self._clear_btn, self._del_btn, self._up_btn, self._down_btn,
                    self._cache_btn]:
            btn.setStyleSheet(btn_s)

        list_s = (f"QListWidget {{ background-color: {t.bg_secondary}; border: none; "
                  f"font-size: 11px; color: {t.text_primary}; }}"
                  f"QListWidget::item {{ padding: 3px; }}"
                  f"QListWidget::item:selected {{ background-color: {t.bg_active}; }}")
        self._list.setStyleSheet(list_s)
        self._grid.setStyleSheet(list_s)

        self._zoom_label.setStyleSheet(
            f"color: {t.text_secondary}; font-size: 10px; font-weight: 500;")
        self._zoom_slider.setStyleSheet(
            f"QSlider::groove:horizontal {{ background: {t.border}; height: 4px; }}"
            f"QSlider::handle:horizontal {{ background: {t.text_secondary}; "
            f"width: 12px; margin: -4px 0; }}")

        self._cache_size_label.setStyleSheet(
            f"color: {t.text_secondary}; font-size: 10px; font-weight: 500;")

        self._update_view_buttons()
        self._update_cache_size()

    def _update_cache_size(self):
        size = CacheManager().size()
        if size > 0:
            self._cache_btn.setVisible(True)
            self._cache_size_label.setText(CacheManager.format_size(size))
            self._cache_size_label.setVisible(True)
        else:
            self._cache_btn.setVisible(False)
            self._cache_size_label.setVisible(False)

    def _clear_cache(self):
        CacheManager().clear()
        self._update_cache_size()

    def _update_view_buttons(self):
        t = self.theme
        active_s = (f"background-color: {t.bg_active}; color: {t.text_primary}; "
                    f"border: 1px solid {t.border_active}; font-size: 10px; "
                    f"font-weight: bold; padding: 3px 6px;")
        inactive_s = (f"background-color: {t.bg_button}; color: {t.text_button}; "
                      f"border: 1px solid {t.border}; font-size: 10px; "
                      f"font-weight: 500; padding: 3px 6px;")
        self._list_btn.setStyleSheet(active_s if self._view_mode == "list" else inactive_s)
        self._grid_btn.setStyleSheet(active_s if self._view_mode == "grid" else inactive_s)

    # ------------------------------------------------------------------ View mode

    def _set_view_mode(self, mode):
        self._view_mode = mode
        if mode == "list":
            self._stack.setCurrentWidget(self._list)
        else:
            self._stack.setCurrentWidget(self._grid)
        self._update_view_buttons()
        self._update_bottom_controls()
        self._rebuild()

    def _update_bottom_controls(self):
        is_list = self._view_mode == "list"
        self._up_btn.setVisible(is_list)
        self._down_btn.setVisible(is_list)
        self._zoom_label.setVisible(not is_list)
        self._zoom_slider.setVisible(not is_list)
        self._list_btn.setVisible(True)
        self._grid_btn.setVisible(True)

    def _on_zoom(self, value):
        self._grid.setIconSize(QSize(value, value))
        self._rebuild_grid()

    # ------------------------------------------------------------------ Rebuild

    def _rebuild(self):
        if self._view_mode == "list":
            self._rebuild_list()
        else:
            self._rebuild_grid()
        self._count_label.setText(f"Изображения — {len(self.images)}")

    @staticmethod
    def _short_name(path, max_len=20):
        name = os.path.basename(path)
        if len(name) <= max_len:
            return name
        stem, ext = os.path.splitext(name)
        keep = max_len - len(ext) - 1  # 1 for ellipsis char
        if keep < 2:
            return name[:max_len]
        left = (keep + 1) // 2
        right = keep - left
        return stem[:left] + "\u2026" + stem[-right:] + ext

    def _get_pixmap(self, path):
        pix = self._pix_cache.get(path)
        if pix is None:
            pix = QPixmap(path)
            if not pix.isNull():
                pix = pix.scaled(GRID_MAX, GRID_MAX,
                                 Qt.AspectRatioMode.KeepAspectRatio,
                                 Qt.TransformationMode.SmoothTransformation)
            self._pix_cache[path] = pix
        return pix

    def _style_item(self, item, img):
        t = self.theme
        if img.timer == 0:
            item.setForeground(QBrush(QColor(t.text_hint)))
        else:
            item.setForeground(QBrush(QColor(t.text_primary)))

    def _format_item_text(self, i, img):
        name = self._short_name(img.path)
        if img.timer == 0:
            return f"{i + 1}.  {name}    —"
        return f"{i + 1}.  {name}    {format_time(img.timer)}"

    def _rebuild_list(self):
        # Fast path: update text only if same images in same order
        if self._list.count() == len(self.images):
            same = True
            for i, img in enumerate(self.images):
                item = self._list.item(i)
                idx = item.data(Qt.ItemDataRole.UserRole)
                if idx != i:
                    same = False
                    break
            if same:
                for i, img in enumerate(self.images):
                    item = self._list.item(i)
                    item.setText(self._format_item_text(i, img))
                    self._style_item(item, img)
                return

        self._list.clear()
        for i, img in enumerate(self.images):
            text = self._format_item_text(i, img)
            item = QListWidgetItem(text)
            pix = self._get_pixmap(img.path)
            if not pix.isNull():
                item.setIcon(QIcon(pix))
            item.setData(Qt.ItemDataRole.UserRole, i)
            self._style_item(item, img)
            self._list.addItem(item)

    def _rebuild_grid(self):
        # Fast path: update text only if same images
        if self._grid.count() == len(self.images):
            same = True
            for i in range(self._grid.count()):
                if self._grid.item(i).data(Qt.ItemDataRole.UserRole) != i:
                    same = False
                    break
            if same:
                for i, img in enumerate(self.images):
                    item = self._grid.item(i)
                    item.setText("—" if img.timer == 0 else format_time(img.timer))
                    self._style_item(item, img)
                return

        self._grid.clear()
        sz = self._zoom_slider.value()
        for i, img in enumerate(self.images):
            timer_str = "—" if img.timer == 0 else format_time(img.timer)
            item = QListWidgetItem(timer_str)
            pix = self._get_pixmap(img.path)
            if not pix.isNull():
                scaled = pix.scaled(sz, sz,
                                    Qt.AspectRatioMode.KeepAspectRatio,
                                    Qt.TransformationMode.SmoothTransformation)
                item.setIcon(QIcon(scaled))
            item.setData(Qt.ItemDataRole.UserRole, i)
            self._style_item(item, img)
            self._grid.addItem(item)
        self._grid.setGridSize(QSize(sz + 8, sz + 28))

    def refresh(self, images):
        old_paths = {img.path for img in self.images}
        self.images = list(images)
        new_paths = {img.path for img in self.images}
        if old_paths != new_paths:
            self._pix_cache.clear()
        self._rebuild()

    def _emit(self):
        self.images_updated.emit(self.images)

    # ------------------------------------------------------------------ Actions

    def _add_files(self):
        exts = " ".join(f"*{e}" for e in SUPPORTED_FORMATS)
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Выберите файлы", "",
            f"Изображения ({exts});;Все файлы (*)")
        if paths:
            for p in filter_image_files(paths):
                self.images.append(ImageItem(path=p, timer=300))
            self._rebuild()
            self._emit()

    def _add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку")
        if folder:
            for p in scan_folder(folder):
                self.images.append(ImageItem(path=p, timer=300))
            self._rebuild()
            self._emit()

    def _add_from_url(self):
        from ui.url_dialog import UrlDialog
        timer = 300
        if self._parent and hasattr(self._parent, "get_timer_seconds"):
            timer = self._parent.get_timer_seconds()
        dlg = UrlDialog(self.theme, timer=timer, parent=self)
        dlg.images_loaded.connect(self._on_url_images)
        dlg.exec()

    def _on_url_images(self, images):
        for img in images:
            self.images.append(img)
        self._pix_cache.clear()
        self._rebuild()
        self._emit()
        self._update_cache_size()

    def _clear(self):
        self.images = []
        self._rebuild()
        self._emit()

    def _move_up(self):
        row = self._list.currentRow()
        if row > 0:
            self.images[row], self.images[row - 1] = self.images[row - 1], self.images[row]
            self._rebuild()
            self._list.setCurrentRow(row - 1)
            self._emit()

    def _move_down(self):
        row = self._list.currentRow()
        if 0 <= row < len(self.images) - 1:
            self.images[row], self.images[row + 1] = self.images[row + 1], self.images[row]
            self._rebuild()
            self._list.setCurrentRow(row + 1)
            self._emit()

    def _on_reorder(self):
        new_order = []
        for i in range(self._list.count()):
            item = self._list.item(i)
            orig_idx = item.data(Qt.ItemDataRole.UserRole)
            if orig_idx is not None and orig_idx < len(self.images):
                new_order.append(self.images[orig_idx])
        if new_order:
            self.images = new_order
            self._rebuild()
            self._emit()

    def _on_grid_reorder(self):
        new_order = []
        for i in range(self._grid.count()):
            item = self._grid.item(i)
            orig_idx = item.data(Qt.ItemDataRole.UserRole)
            if orig_idx is not None and orig_idx < len(self.images):
                new_order.append(self.images[orig_idx])
        if new_order:
            self.images = new_order
            self._rebuild()
            self._emit()

    def _delete_selected(self):
        if self._view_mode == "list":
            widget = self._list
        else:
            widget = self._grid
        rows = sorted([idx.row() for idx in widget.selectedIndexes()], reverse=True)
        for row in rows:
            if 0 <= row < len(self.images):
                self.images.pop(row)
        self._rebuild()
        self._emit()

    def closeEvent(self, event):
        if self._parent and hasattr(self._parent, "_on_editor_close"):
            self._parent._on_editor_close()
        super().closeEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            self._delete_selected()
        else:
            super().keyPressEvent(event)
