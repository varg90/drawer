import os
from PyQt6.QtWidgets import QListWidget, QListWidgetItem
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import Qt, pyqtSignal, QSize


class ImageListWidget(QListWidget):
    order_changed = pyqtSignal()
    selection_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.setStyleSheet("""
            QListWidget { background-color: #2b2b3d; border: none; border-radius: 6px; }
            QListWidget::item { padding: 4px; }
            QListWidget::item:selected { background-color: #3a3a6a; }
        """)
        self.setIconSize(QSize(48, 48))
        self.model().rowsMoved.connect(lambda: self.order_changed.emit())
        self.currentRowChanged.connect(lambda row: self.selection_changed.emit(row))
        self._show_filenames = False
        self._images = []

    def set_images(self, images):
        self._images = images
        self._rebuild()

    def set_show_filenames(self, show):
        self._show_filenames = show
        self._rebuild()

    def _rebuild(self):
        self.clear()
        for i, img in enumerate(self._images):
            text = f"{i+1}. {os.path.basename(img.path)}" if self._show_filenames else f"{i+1}."
            item = QListWidgetItem(text)
            pix = QPixmap(img.path)
            if not pix.isNull():
                pix = pix.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio,
                                  Qt.TransformationMode.SmoothTransformation)
                item.setIcon(QIcon(pix))
            secs = img.timer
            if secs >= 3600:
                t = f"{secs//3600}ч {(secs%3600)//60}мин"
            elif secs >= 60:
                t = f"{secs//60} мин"
            else:
                t = f"{secs} сек"
            item.setToolTip(f"Таймер: {t}")
            item.setData(Qt.ItemDataRole.UserRole, i)
            self.addItem(item)

    def get_ordered_images(self):
        result = []
        for i in range(self.count()):
            item = self.item(i)
            if item:
                orig_idx = item.data(Qt.ItemDataRole.UserRole)
                if orig_idx is not None and orig_idx < len(self._images):
                    result.append(self._images[orig_idx])
        return result if result else self._images

    def move_current_up(self):
        row = self.currentRow()
        if row > 0:
            self._images[row], self._images[row-1] = self._images[row-1], self._images[row]
            self._rebuild()
            self.setCurrentRow(row - 1)

    def move_current_down(self):
        row = self.currentRow()
        if row < len(self._images) - 1:
            self._images[row], self._images[row+1] = self._images[row+1], self._images[row]
            self._rebuild()
            self.setCurrentRow(row + 1)

    def delete_current(self):
        row = self.currentRow()
        if 0 <= row < len(self._images):
            self._images.pop(row)
            self._rebuild()
            if self._images:
                self.setCurrentRow(min(row, len(self._images) - 1))
