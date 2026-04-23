# ui/editor_panel/pixmap_loader.py
"""Background pixmap loader thread for the editor grid."""

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QImage

from ui.scales import S


class PixmapLoader(QThread):
    """Load images from disk in a background thread."""
    loaded = pyqtSignal(str, QImage)

    def __init__(self, paths, max_size=None):
        super().__init__()
        self._paths = paths
        self._max = max_size if max_size is not None else S.GRID_MAX
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        for path in self._paths:
            if self._cancel:
                return
            img = QImage(path)
            if not img.isNull():
                img = img.scaled(
                    self._max, self._max,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.loaded.emit(path, img)
