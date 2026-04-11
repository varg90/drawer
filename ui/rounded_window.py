"""Mixin for painting frameless windows with rounded corners."""

from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QPainterPath, QColor, QLinearGradient
from PyQt6.QtWidgets import QWidget

from ui.scales import S


class RoundedWindowMixin:
    """Adds rounded-corner painting to frameless windows.

    Call rounded_init() in __init__ after the Qt widget is constructed.
    Override corner_radii() to control per-corner rounding.
    Override _bg_color() for solid background or _bg_brush() for gradient.
    Call _paint_rounded(event) from paintEvent().
    """

    def rounded_init(self):
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def corner_radii(self):
        """Return (top_left, top_right, bottom_right, bottom_left) radii."""
        r = S.WINDOW_RADIUS
        return (r, r, r, r)

    def _bg_color(self):
        """Override to return the window background QColor."""
        return QColor("#16120e")

    def _bg_brush(self):
        """Override to return QColor or QLinearGradient. Defaults to _bg_color()."""
        return self._bg_color()

    def _paint_rounded(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        tl, tr, br, bl = self.corner_radii()
        rect = QRectF(self.rect())
        path = QPainterPath()

        if tl == tr == br == bl:
            path.addRoundedRect(rect, tl, tl)
        else:
            # Build path with per-corner radii
            d = 2  # diameter multiplier
            path.moveTo(rect.left() + tl, rect.top())
            path.lineTo(rect.right() - tr, rect.top())
            if tr:
                path.arcTo(rect.right() - d*tr, rect.top(), d*tr, d*tr, 90, -90)
            else:
                path.lineTo(rect.right(), rect.top())
            path.lineTo(rect.right(), rect.bottom() - br)
            if br:
                path.arcTo(rect.right() - d*br, rect.bottom() - d*br, d*br, d*br, 0, -90)
            else:
                path.lineTo(rect.right(), rect.bottom())
            path.lineTo(rect.left() + bl, rect.bottom())
            if bl:
                path.arcTo(rect.left(), rect.bottom() - d*bl, d*bl, d*bl, -90, -90)
            else:
                path.lineTo(rect.left(), rect.bottom())
            path.lineTo(rect.left(), rect.top() + tl)
            if tl:
                path.arcTo(rect.left(), rect.top(), d*tl, d*tl, 180, -90)
            else:
                path.lineTo(rect.left(), rect.top())
            path.closeSubpath()

        painter.fillPath(path, self._bg_brush())
        painter.end()
