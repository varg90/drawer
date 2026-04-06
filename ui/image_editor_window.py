import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QLabel, QListWidget, QListWidgetItem, QFileDialog,
                              QAbstractItemView)
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from core.constants import SUPPORTED_FORMATS
from core.file_utils import filter_image_files, scan_folder
from core.models import ImageItem
from core.timer_logic import format_time


class ImageEditorWindow(QWidget):
    images_updated = pyqtSignal(list)

    def __init__(self, images, theme, parent=None):
        super().__init__()
        self.images = list(images)  # work on a copy
        self.theme = theme
        self._parent = parent
        self.setWindowTitle("Изображения")
        self.setMinimumSize(340, 400)

        self._build_ui()
        self._apply_theme()
        self._rebuild_list()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 8, 12, 8)
        root.setSpacing(8)

        # Header
        header = QHBoxLayout()
        self._count_label = QLabel("")
        header.addWidget(self._count_label)
        header.addStretch()
        close_btn = QPushButton("x")
        close_btn.setFixedSize(20, 20)
        close_btn.clicked.connect(self.close)
        header.addWidget(close_btn)
        root.addLayout(header)

        # Toolbar
        toolbar = QHBoxLayout()
        self._add_files_btn = QPushButton("+ Файлы")
        self._add_files_btn.clicked.connect(self._add_files)
        toolbar.addWidget(self._add_files_btn)
        self._add_folder_btn = QPushButton("+ Папка")
        self._add_folder_btn.clicked.connect(self._add_folder)
        toolbar.addWidget(self._add_folder_btn)
        toolbar.addStretch()
        self._del_btn = QPushButton("x")
        self._del_btn.clicked.connect(self._delete_selected)
        toolbar.addWidget(self._del_btn)
        self._clear_btn = QPushButton("Очистить")
        self._clear_btn.clicked.connect(self._clear)
        toolbar.addWidget(self._clear_btn)
        root.addLayout(toolbar)

        # File list
        self._list = QListWidget()
        self._list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self._list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self._list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self._list.setIconSize(QSize(28, 28))
        self._list.model().rowsMoved.connect(self._on_reorder)
        root.addWidget(self._list)

        # Bottom controls
        bottom = QHBoxLayout()
        bottom.addStretch()
        self._up_btn = QPushButton("^")
        self._up_btn.setFixedSize(30, 24)
        self._up_btn.clicked.connect(self._move_up)
        bottom.addWidget(self._up_btn)
        self._down_btn = QPushButton("v")
        self._down_btn.setFixedSize(30, 24)
        self._down_btn.clicked.connect(self._move_down)
        bottom.addWidget(self._down_btn)
        bottom.addStretch()
        root.addLayout(bottom)

    def _apply_theme(self):
        t = self.theme
        self.setStyleSheet(f"background-color: {t.bg}; color: {t.text_primary};")

        self._count_label.setStyleSheet(f"color: {t.text_secondary}; font-size: 12px; font-weight: 500;")

        btn_s = (f"background-color: {t.bg_button}; color: {t.text_button}; "
                 f"border: 1px solid {t.border}; font-size: 10px; font-weight: 500; padding: 3px 8px;")
        for btn in [self._add_files_btn, self._add_folder_btn, self._clear_btn,
                    self._del_btn, self._up_btn, self._down_btn]:
            btn.setStyleSheet(btn_s)

        self._list.setStyleSheet(
            f"QListWidget {{ background-color: {t.bg_secondary}; border: none; }}"
            f"QListWidget::item {{ padding: 3px; }}"
            f"QListWidget::item:selected {{ background-color: {t.bg_active}; }}")

    def _rebuild_list(self):
        self._list.clear()
        for i, img in enumerate(self.images):
            name = os.path.basename(img.path)
            timer_str = format_time(img.timer)
            text = f"{i + 1}.  {name}    {timer_str}"
            item = QListWidgetItem(text)
            pix = QPixmap(img.path)
            if not pix.isNull():
                pix = pix.scaled(28, 28,
                                 Qt.AspectRatioMode.KeepAspectRatio,
                                 Qt.TransformationMode.SmoothTransformation)
                item.setIcon(QIcon(pix))
            item.setData(Qt.ItemDataRole.UserRole, i)
            self._list.addItem(item)
        self._count_label.setText(f"Изображения — {len(self.images)}")

    def refresh(self, images):
        self.images = list(images)
        self._rebuild_list()

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
            self._rebuild_list()
            self._emit()

    def _add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку")
        if folder:
            for p in scan_folder(folder):
                self.images.append(ImageItem(path=p, timer=300))
            self._rebuild_list()
            self._emit()

    def _clear(self):
        self.images = []
        self._rebuild_list()
        self._emit()

    def _move_up(self):
        row = self._list.currentRow()
        if row > 0:
            self.images[row], self.images[row - 1] = self.images[row - 1], self.images[row]
            self._rebuild_list()
            self._list.setCurrentRow(row - 1)
            self._emit()

    def _move_down(self):
        row = self._list.currentRow()
        if 0 <= row < len(self.images) - 1:
            self.images[row], self.images[row + 1] = self.images[row + 1], self.images[row]
            self._rebuild_list()
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
            self._rebuild_list()
            self._emit()

    def _delete_selected(self):
        rows = sorted([idx.row() for idx in self._list.selectedIndexes()], reverse=True)
        for row in rows:
            if 0 <= row < len(self.images):
                self.images.pop(row)
        self._rebuild_list()
        self._emit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            self._delete_selected()
        else:
            super().keyPressEvent(event)
