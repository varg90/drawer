"""Reusable widget factories for Drawer UI."""
import qtawesome as qta
from PyQt6.QtWidgets import QPushButton, QLabel, QHBoxLayout, QWidget
from PyQt6.QtCore import Qt, QSize, QRect, pyqtSignal
from PyQt6.QtGui import QPainter, QFont, QFontMetrics, QColor, QImage, QPixmap
from ui.scales import S
from ui.icons import Icons


def _crop_transparent(img):
    """Crop transparent borders from a QImage, return the tight bounding QImage."""
    top = bot = left = right = 0
    for top in range(img.height()):
        if any(img.pixelColor(x, top).alpha() > 0 for x in range(img.width())):
            break
    for bot in range(img.height() - 1, -1, -1):
        if any(img.pixelColor(x, bot).alpha() > 0 for x in range(img.width())):
            break
    for left in range(img.width()):
        if any(img.pixelColor(left, y).alpha() > 0 for y in range(img.height())):
            break
    for right in range(img.width() - 1, -1, -1):
        if any(img.pixelColor(right, y).alpha() > 0 for y in range(img.height())):
            break
    return img.copy(QRect(left, top, right - left + 1, bot - top + 1))


class IconButton(QWidget):
    """Clickable icon widget — paints icon scaled to fill widget, no padding."""
    clicked = pyqtSignal()

    def __init__(self, size=S.ICON_HEADER, parent=None):
        super().__init__(parent)
        self._size = size
        self._pixmap = None
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def setIcon(self, icon):
        big = int(self._size * 2)
        raw = icon.pixmap(QSize(big, big)).toImage()
        cropped = _crop_transparent(raw)
        self._pixmap = QPixmap.fromImage(cropped).scaled(
            self._size, self._size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation)
        self.update()

    def paintEvent(self, event):
        if self._pixmap:
            x = (self._size - self._pixmap.width()) // 2
            y = (self._size - self._pixmap.height()) // 2
            QPainter(self).drawPixmap(x, y, self._pixmap)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()


def make_icon_btn(icon_name, color, size=S.ICON_HEADER, tooltip=""):
    """Small icon button — pixmap fills full widget, no internal padding."""
    btn = IconButton(size)
    btn.setIcon(qta.icon(icon_name, color=color))
    if tooltip:
        btn.setToolTip(tooltip)
    return btn


def make_start_btn(theme):
    """Square start button with fa6s.pencil icon."""
    size = S.ICON_START
    icon_sz = int(size * S.START_ICON_RATIO)
    radius = int(size * S.START_RADIUS_RATIO)
    btn = QPushButton()
    btn.setIcon(qta.icon(Icons.START, color=theme.start_text))
    btn.setIconSize(QSize(icon_sz, icon_sz))
    btn.setFixedSize(size, size)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet(
        f"background-color: {theme.start_bg}; border: none; "
        f"border-radius: {radius}px;")
    return btn


def make_icon_toggle(icon_on, icon_off, is_on, theme, size=S.ICON_HEADER):
    """Toggle button that switches between two icons."""
    btn = IconButton(size)
    icon_name = icon_on if is_on else icon_off
    color = theme.accent if is_on else theme.text_hint
    btn.setIcon(qta.icon(icon_name, color=color))
    return btn


class _TitlePixmap(QWidget):
    """Title rendered as a cropped pixmap — widget bounds = visible pixels."""
    def __init__(self, text, color, font_size, weight=500, spacing=3,
                 target_width=None, parent=None):
        super().__init__(parent)
        self._color = color
        self._text = text
        self._font_size = font_size
        self._weight = weight
        self._spacing = spacing
        self._target_width = target_width
        self._render(color)

    def _render(self, color):
        font = QFont()
        font.setPixelSize(self._font_size)
        font.setWeight(QFont.Weight(self._weight))
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, self._spacing)
        fm = QFontMetrics(font)
        w = fm.horizontalAdvance(self._text) + 20
        h = fm.height() + 10
        img = QImage(w, h, QImage.Format.Format_ARGB32)
        img.fill(QColor(0, 0, 0, 0))
        p = QPainter(img)
        p.setFont(font)
        p.setPen(QColor(color))
        p.drawText(img.rect(), Qt.AlignmentFlag.AlignCenter, self._text)
        p.end()
        cropped = _crop_transparent(img)
        pm = QPixmap.fromImage(cropped)
        if self._target_width and pm.width() != self._target_width:
            pm = pm.scaled(
                self._target_width,
                pm.height() * self._target_width // pm.width(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation)
        self._pixmap = pm
        self.setFixedSize(self._pixmap.width(), self._pixmap.height())
        self.update()

    def recolor(self, color):
        if color == self._color:
            return
        self._color = color
        self._render(color)

    def paintEvent(self, event):
        QPainter(self).drawPixmap(0, 0, self._pixmap)


def make_centered_header(title_text, left_widgets, right_widgets, theme):
    """Header row: title as cropped pixmap, all items aligned to top margin."""
    title = _TitlePixmap(title_text, theme.text_header, S.FONT_TITLE,
                         target_width=S.TITLE_W)

    header = QHBoxLayout()
    header.setContentsMargins(0, 0, 0, 0)
    header.setSpacing(6)

    for w in left_widgets:
        header.addWidget(w, 0, Qt.AlignmentFlag.AlignTop)
    header.addStretch(1)
    header.addWidget(title, 0, Qt.AlignmentFlag.AlignTop)
    header.addStretch(1)
    for w in right_widgets:
        header.addWidget(w, 0, Qt.AlignmentFlag.AlignTop)

    return header, title


def timer_btn_style(is_active, theme):
    """Return stylesheet for active/inactive timer button."""
    if is_active:
        return (f"background-color: {theme.start_bg}; color: {theme.start_text}; "
                f"border: none; "
                f"font-size: {S.FONT_BUTTON}px; font-weight: 600; "
                f"padding: {S.TIMER_BTN_PADDING_V}px {S.TIMER_BTN_PADDING_H}px;")
    return (f"background-color: {theme.bg_button}; color: {theme.text_secondary}; "
            f"border: none; "
            f"font-size: {S.FONT_BUTTON}px; "
            f"padding: {S.TIMER_BTN_PADDING_V}px {S.TIMER_BTN_PADDING_H}px;")


def make_timer_btn(label, is_active, theme):
    """Timer preset or tier button."""
    btn = QPushButton(label)
    btn.setStyleSheet(timer_btn_style(is_active, theme))
    return btn
