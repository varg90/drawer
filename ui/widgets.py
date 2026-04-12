"""Reusable widget factories for Drawer UI."""
import qtawesome as qta
from PyQt6.QtWidgets import QPushButton, QLabel, QHBoxLayout, QWidget
from PyQt6.QtCore import Qt, QSize, QRect, pyqtSignal
from PyQt6.QtGui import QPainter, QFont, QColor, QPixmap, QImage
from ui.scales import S, TEXT_SHADOW_OFFSET
from ui.icons import Icons


def _crop_transparent(img):
    """Crop transparent borders from a QImage via raw byte access."""
    img = img.convertToFormat(QImage.Format.Format_ARGB32)
    w, h = img.width(), img.height()
    if w == 0 or h == 0:
        return img
    bpl = img.bytesPerLine()
    ptr = img.bits()
    ptr.setsize(bpl * h)
    data = bytes(ptr)
    # ARGB32 little-endian: each pixel is [B, G, R, A] — alpha at offset 3
    top = next((y for y in range(h)
                if any(data[y * bpl + x * 4 + 3] for x in range(w))), 0)
    bot = next((y for y in range(h - 1, top - 1, -1)
                if any(data[y * bpl + x * 4 + 3] for x in range(w))), top)
    left = next((x for x in range(w)
                 if any(data[y * bpl + x * 4 + 3] for y in range(top, bot + 1))), 0)
    right = next((x for x in range(w - 1, left - 1, -1)
                  if any(data[y * bpl + x * 4 + 3] for y in range(top, bot + 1))), left)
    return img.copy(left, top, right - left + 1, bot - top + 1)


class IconButton(QWidget):
    """Clickable icon widget — renders at native DPI for sharp display."""
    clicked = pyqtSignal()

    def __init__(self, size=S.ICON_HEADER, parent=None):
        super().__init__(parent)
        self._size = size
        self._pixmap = None
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def setIcon(self, icon):
        ratio = max(self.devicePixelRatioF(), 2.0)
        phys = int(self._size * ratio)
        raw = icon.pixmap(QSize(phys, phys)).toImage()
        cropped = _crop_transparent(raw)
        pm = QPixmap.fromImage(cropped).scaled(
            phys, phys,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation)
        pm.setDevicePixelRatio(ratio)
        self._pixmap = pm
        self.update()

    def paintEvent(self, event):
        if self._pixmap:
            ratio = self._pixmap.devicePixelRatio()
            lw = self._pixmap.width() / ratio
            lh = self._pixmap.height() / ratio
            x = (self._size - lw) / 2
            y = (self._size - lh) / 2
            QPainter(self).drawPixmap(int(x), int(y), self._pixmap)

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


class RoundedIconButton(QWidget):
    """Square button with rounded background and vector icon painted to fill."""
    clicked = pyqtSignal()

    def __init__(self, icon_name, icon_color, bg_color, size, icon_ratio=1.0,
                 radius_ratio=S.START_RADIUS_RATIO, parent=None):
        super().__init__(parent)
        self._icon = qta.icon(icon_name, color=icon_color)
        self._bg = QColor(bg_color)
        self._size = size
        self._icon_ratio = icon_ratio
        self._radius = int(size * radius_ratio)
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_icon(self, icon_name, color):
        self._icon = qta.icon(icon_name, color=color)
        self.update()

    def set_bg(self, color):
        self._bg = QColor(color)
        self.update()

    def paintEvent(self, event):
        from PyQt6.QtGui import QPainterPath
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Rounded background
        path = QPainterPath()
        path.addRoundedRect(0.0, 0.0, self._size, self._size,
                            self._radius, self._radius)
        p.fillPath(path, self._bg)
        # Vector icon
        icon_sz = int(self._size * self._icon_ratio)
        margin = (self._size - icon_sz) // 2
        self._icon.paint(p, margin, margin, icon_sz, icon_sz)
        p.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()


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
        f"background-color: {theme.start_bg}; "
        f"border-radius: {radius}px; border: none;")
    return btn


def make_icon_toggle(icon_on, icon_off, is_on, theme, size=S.ICON_HEADER):
    """Toggle button that switches between two icons."""
    btn = IconButton(size)
    icon_name = icon_on if is_on else icon_off
    color = theme.accent if is_on else theme.text_hint
    btn.setIcon(qta.icon(icon_name, color=color))
    return btn


class TitleLabel(QLabel):
    """Title with embossed text effect — light highlight above, dark shadow below."""
    def __init__(self, text, color, font_size, weight=500, spacing=3,
                 target_width=None, parent=None):
        super().__init__(text, parent)
        self._color = QColor(color)
        self._text = text
        self._font = QFont("Lora")
        self._font.setPixelSize(font_size)
        self._font.setWeight(QFont.Weight(weight))
        if spacing:
            self._font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, spacing)
        self.setFont(self._font)
        self.setStyleSheet("color: transparent; background: transparent;")
        self.setContentsMargins(0, 0, 0, 0)
        if target_width:
            self.setFixedWidth(target_width)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def recolor(self, color):
        c = QColor(color)
        if c == self._color:
            return
        self._color = c
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        p.setFont(self._font)
        n = S.TITLE_Y_NUDGE
        rect = self.rect().adjusted(0, -n, 0, -n)
        flags = self.alignment() | Qt.TextFlag.TextSingleLine
        # Shadow above (dark, pressed-in look)
        p.setPen(QColor(0, 0, 0, 128))
        shadow_rect = rect.adjusted(0, -TEXT_SHADOW_OFFSET, 0, -TEXT_SHADOW_OFFSET)
        p.drawText(shadow_rect, flags, self._text)
        # Highlight below (subtle light edge)
        p.setPen(QColor(255, 250, 240, 10))
        highlight_rect = rect.adjusted(0, TEXT_SHADOW_OFFSET, 0, TEXT_SHADOW_OFFSET)
        p.drawText(highlight_rect, flags, self._text)
        # Main text
        p.setPen(self._color)
        p.drawText(rect, flags, self._text)
        p.end()


def make_centered_header(title_text, left_widgets, right_widgets, theme):
    """Header row: title label, all items aligned to top margin."""
    title = TitleLabel(title_text, theme.text_header, S.FONT_TITLE,
                       weight=500, spacing=1.5, target_width=S.TITLE_W)

    header = QHBoxLayout()
    header.setContentsMargins(0, 0, 0, 0)
    header.setSpacing(S.SPACING_HEADER)

    for w in left_widgets:
        header.addWidget(w, 0, Qt.AlignmentFlag.AlignTop)
    header.addStretch(1)
    header.addWidget(title, 0, Qt.AlignmentFlag.AlignTop)
    header.addStretch(1)
    for w in right_widgets:
        header.addWidget(w, 0, Qt.AlignmentFlag.AlignTop)

    return header, title


def timer_btn_style(active, theme):
    """Return stylesheet for active/inactive timer button."""
    if active:
        bg, fg, fw = theme.start_bg, theme.bg_panel, 500
    else:
        bg, fg, fw = theme.bg_button, theme.text_secondary, 400
    return (
        f"background-color: {bg}; color: {fg}; "
        f"font-family: 'Lexend'; font-size: {S.FONT_BUTTON}px; font-weight: {fw}; "
        f"padding: {S.TIMER_BTN_PADDING_V}px {S.TIMER_BTN_PADDING_H}px; "
        f"border-radius: {S.TIMER_BTN_RADIUS}px; border: none;"
    )


def make_timer_btn(label, is_active, theme, parent=None):
    """Timer preset or tier button."""
    btn = QPushButton(label, parent)
    btn.setStyleSheet(timer_btn_style(is_active, theme))
    return btn

