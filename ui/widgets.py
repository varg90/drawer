"""Reusable widget factories for RefBot UI."""
import qtawesome as qta
from PyQt6.QtWidgets import QPushButton, QLabel, QHBoxLayout, QWidget
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QPainter, QFont, QColor, QFontMetrics
from ui.scales import S
from ui.icons import Icons


def make_title_pixmap(text, color, font_size=S.FONT_TITLE, letter_spacing=3):
    """Render title text as a tight pixmap with no font padding above glyphs."""
    font = QFont()
    font.setPixelSize(font_size)
    font.setWeight(QFont.Weight.Medium)
    font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, letter_spacing)
    fm = QFontMetrics(font)
    # tightBoundingRect gives pixel-exact bounds of the visible glyphs
    tight = fm.tightBoundingRect(text)
    w = tight.width() + 2  # small horizontal buffer
    h = tight.height()
    pix = QPixmap(w, h)
    pix.fill(QColor(0, 0, 0, 0))
    p = QPainter(pix)
    p.setFont(font)
    p.setPen(QColor(color))
    # Draw at baseline offset so glyphs start at y=0
    p.drawText(0, -tight.top(), text)
    p.end()
    return pix


def make_icon_btn(icon_name, color, size=S.ICON_HEADER, tooltip=""):
    """Small icon button with no background/border."""
    btn = QPushButton()
    icon_sz = int(size * 1.3)  # oversize to compensate for glyph padding
    btn.setIcon(qta.icon(icon_name, color=color))
    btn.setIconSize(QSize(icon_sz, icon_sz))
    btn.setFixedSize(size, size)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet("background: transparent; border: none; padding: 0px;")
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
    btn = QPushButton()
    icon_name = icon_on if is_on else icon_off
    color = theme.accent if is_on else theme.text_hint
    icon_sz = int(size * 1.3)
    btn.setIcon(qta.icon(icon_name, color=color))
    btn.setIconSize(QSize(icon_sz, icon_sz))
    btn.setFixedSize(size, size)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet("background: transparent; border: none; padding: 0px;")
    return btn


def make_centered_header(title_text, left_widgets, right_widgets, theme):
    """Header row with title centered via equal stretch containers."""
    header = QHBoxLayout()
    header.setContentsMargins(0, 0, 0, 0)
    header.setSpacing(0)

    for w in left_widgets:
        header.addWidget(w, 0, Qt.AlignmentFlag.AlignTop)
    header.addStretch()

    title = QLabel()
    title.setPixmap(make_title_pixmap(title_text, theme.text_header))
    title.setStyleSheet("background: transparent;")
    header.addWidget(title, 0, Qt.AlignmentFlag.AlignTop)

    header.addStretch()
    for w in right_widgets:
        header.addWidget(w, 0, Qt.AlignmentFlag.AlignTop)
    return header, title


def make_timer_btn(label, is_active, theme):
    """Timer preset or tier button."""
    btn = QPushButton(label)
    if is_active:
        btn.setStyleSheet(
            f"background-color: {theme.bg_active}; color: {theme.text_primary}; "
            f"border: 1px solid {theme.border_active}; "
            f"font-size: {S.FONT_BUTTON}px; "
            f"padding: {S.TIMER_BTN_PADDING_V}px {S.TIMER_BTN_PADDING_H}px;")
    else:
        btn.setStyleSheet(
            f"background-color: {theme.bg_button}; color: {theme.text_secondary}; "
            f"border: 1px solid {theme.border}; "
            f"font-size: {S.FONT_BUTTON}px; "
            f"padding: {S.TIMER_BTN_PADDING_V}px {S.TIMER_BTN_PADDING_H}px;")
    return btn
