# ui/accent_picker.py
"""Compact accent color picker — SV square + hue bar + hex input."""
import colorsys
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QImage, QColor, QPixmap
from ui.scales import S, sc


class _ColorSquare(QLabel):
    """Saturation/Value picker for a given hue."""
    def __init__(self, size, parent=None):
        super().__init__(parent)
        self._size = size
        self._hue = 0.0
        self._sat = 0.8
        self._val = 0.6
        self.on_color_changed = None
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self._build()

    def set_hsv(self, h, s, v):
        self._hue = h
        self._sat = s
        self._val = v
        self._build()

    def set_hue(self, h):
        self._hue = h
        self._build()

    def _build(self):
        img = QImage(self._size, self._size, QImage.Format.Format_RGB32)
        for y in range(self._size):
            v = 1.0 - y / (self._size - 1)
            for x in range(self._size):
                s = x / (self._size - 1)
                r, g, b = colorsys.hsv_to_rgb(self._hue, s, v)
                img.setPixelColor(x, y, QColor(int(r*255), int(g*255), int(b*255)))
        self.setPixmap(QPixmap.fromImage(img))

    def mousePressEvent(self, e):
        self._pick(e.position())

    def mouseMoveEvent(self, e):
        self._pick(e.position())

    def _pick(self, pos):
        x = max(0, min(pos.x(), self._size - 1))
        y = max(0, min(pos.y(), self._size - 1))
        self._sat = x / (self._size - 1)
        self._val = 1.0 - y / (self._size - 1)
        if self.on_color_changed:
            self.on_color_changed(self.color())

    def color(self):
        r, g, b = colorsys.hsv_to_rgb(self._hue, self._sat, self._val)
        return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"


class _HueBar(QLabel):
    """Vertical hue spectrum bar."""
    def __init__(self, height, width=12, parent=None):
        super().__init__(parent)
        self._h = height
        self._w = width
        self._hue = 0.0
        self.on_hue_changed = None
        self.setFixedSize(width, height)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self._build()

    def set_hue(self, h):
        self._hue = h

    def _build(self):
        img = QImage(self._w, self._h, QImage.Format.Format_RGB32)
        for y in range(self._h):
            h = y / (self._h - 1)
            r, g, b = colorsys.hsv_to_rgb(h, 1.0, 1.0)
            c = QColor(int(r*255), int(g*255), int(b*255))
            for x in range(self._w):
                img.setPixelColor(x, y, c)
        self.setPixmap(QPixmap.fromImage(img))

    def mousePressEvent(self, e):
        self._pick(e.position())

    def mouseMoveEvent(self, e):
        self._pick(e.position())

    def _pick(self, pos):
        y = max(0, min(pos.y(), self._h - 1))
        self._hue = y / (self._h - 1)
        if self.on_hue_changed:
            self.on_hue_changed(self._hue)


class AccentPicker(QWidget):
    """Compact frameless accent color picker window."""
    color_changed = pyqtSignal(str)

    def __init__(self, current_color, theme, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.theme = theme
        self._build_ui(current_color)
        self._apply_theme()
        self.installEventFilter(self)

    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent
        if event.type() == QEvent.Type.WindowDeactivate:
            self.close()
            return True
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def _build_ui(self, current_color):
        root = QVBoxLayout(self)
        root.setContentsMargins(S.ACCENT_MARGIN, S.ACCENT_MARGIN, S.ACCENT_MARGIN, S.ACCENT_MARGIN)
        root.setSpacing(S.ACCENT_SPACING)

        # Picker row
        row = QHBoxLayout()
        row.setSpacing(S.ACCENT_ROW_SPACING)
        self._square = _ColorSquare(S.ACCENT_SQ)
        self._hue_bar = _HueBar(S.ACCENT_SQ, S.ACCENT_BAR_W)
        self._hue_bar.on_hue_changed = self._on_hue
        self._square.on_color_changed = self._on_sv
        row.addStretch()
        row.addWidget(self._square)
        row.addWidget(self._hue_bar)
        row.addStretch()
        root.addLayout(row)

        # Hex input
        self._hex = QLineEdit(current_color)
        self._hex.setFixedHeight(S.ACCENT_HEX_H)
        self._hex.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hex.returnPressed.connect(self._on_hex)
        root.addWidget(self._hex)

        # Sync picker to current color
        self._sync_to_color(current_color)

    def _apply_theme(self):
        t = self.theme
        self.setStyleSheet(
            f"background: {t.bg}; border: 1px solid {t.border};")
        self._hex.setStyleSheet(
            f"background: {t.bg_button}; color: {t.text_secondary}; "
            f"border: 1px solid {t.border}; border-radius: {S.ACCENT_HEX_RADIUS}px; "
            f"font-size: {S.ACCENT_HEX_FONT}px; font-family: monospace;")

    def _sync_to_color(self, hex_color):
        c = QColor(hex_color)
        h, s, v = c.hueF(), c.saturationF(), c.valueF()
        if h < 0:
            h = 0.0
        self._hue_bar.set_hue(h)
        self._square.set_hsv(h, s, v)

    def _on_hue(self, h):
        self._square.set_hue(h)
        color = self._square.color()
        self._hex.setText(color)
        self.color_changed.emit(color)

    def _on_sv(self, color):
        self._hex.setText(color)
        self.color_changed.emit(color)

    def _on_hex(self):
        text = self._hex.text().strip()
        if not text.startswith("#"):
            text = "#" + text
        c = QColor(text)
        if c.isValid():
            self._hex.setText(c.name())
            self._sync_to_color(c.name())
            self.color_changed.emit(c.name())

    def focusOutEvent(self, e):
        # Close when clicking outside
        super().focusOutEvent(e)

    def show_near(self, widget):
        """Position near the accent button and show."""
        pos = widget.mapToGlobal(widget.rect().bottomLeft())
        self.move(pos.x(), pos.y() + S.ACCENT_OFFSET_Y)
        self.show()
        self.activateWindow()
