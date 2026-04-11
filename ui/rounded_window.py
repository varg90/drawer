"""Mixin for painting frameless windows with rounded corners."""

import random

from PyQt6.QtCore import Qt, QRectF, QRect
from PyQt6.QtGui import (QPainter, QPainterPath, QBrush, QColor, QPen,
                         QLinearGradient, QImage, QPixmap)
from PyQt6.QtWidgets import QWidget

from ui.scales import S


def _dithered_gradient(width, height, grad):
    """Render gradient to QPixmap with per-pixel noise to eliminate banding."""
    img = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)

    # Paint the gradient onto the image
    p = QPainter(img)
    p.fillRect(0, 0, width, height, QBrush(grad))
    p.end()

    # Add subtle noise to break banding — vary each pixel by ±2
    # Only process a sparse grid (every 2nd pixel) for performance
    for y in range(0, height, 2):
        for x in range(0, width, 2):
            c = img.pixelColor(x, y)
            noise = random.randint(-2, 2)
            r = max(0, min(255, c.red() + noise))
            g = max(0, min(255, c.green() + noise))
            b = max(0, min(255, c.blue() + noise))
            img.setPixelColor(x, y, QColor(r, g, b, c.alpha()))

    return QPixmap.fromImage(img)


class RoundedWindowMixin:
    """Adds rounded-corner painting to frameless windows.

    Call rounded_init() in __init__ after the Qt widget is constructed.
    Override corner_radii() to control per-corner rounding.
    Override _bg_color() for solid background or _bg_brush() for gradient.
    Call _paint_rounded(event) from paintEvent().
    """

    def rounded_init(self):
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._rw_cached_path = None
        self._rw_cached_radii = None
        self._rw_cached_rect = None
        self._rw_cached_grad_pm = None
        self._rw_cached_grad_size = None

    def corner_radii(self):
        """Return (top_left, top_right, bottom_right, bottom_left) radii."""
        r = S.WINDOW_RADIUS
        return (r, r, r, r)

    def _bg_color(self):
        """Must be overridden to return the window background QColor."""
        raise NotImplementedError("Subclass must override _bg_color()")

    def _bg_brush(self):
        """Override to return QColor or QLinearGradient. Defaults to _bg_color()."""
        return self._bg_color()

    def _border_color(self):
        """Override to return border QColor, or None for no border."""
        return None

    def _build_path(self, rect, tl, tr, br, bl):
        path = QPainterPath()
        if tl == tr == br == bl:
            path.addRoundedRect(rect, tl, tl)
        else:
            path.moveTo(rect.left() + tl, rect.top())
            path.lineTo(rect.right() - tr, rect.top())
            if tr:
                path.arcTo(rect.right() - 2*tr, rect.top(), 2*tr, 2*tr, 90, -90)
            else:
                path.lineTo(rect.right(), rect.top())
            path.lineTo(rect.right(), rect.bottom() - br)
            if br:
                path.arcTo(rect.right() - 2*br, rect.bottom() - 2*br, 2*br, 2*br, 0, -90)
            else:
                path.lineTo(rect.right(), rect.bottom())
            path.lineTo(rect.left() + bl, rect.bottom())
            if bl:
                path.arcTo(rect.left(), rect.bottom() - 2*bl, 2*bl, 2*bl, -90, -90)
            else:
                path.lineTo(rect.left(), rect.bottom())
            path.lineTo(rect.left(), rect.top() + tl)
            if tl:
                path.arcTo(rect.left(), rect.top(), 2*tl, 2*tl, 180, -90)
            else:
                path.lineTo(rect.left(), rect.top())
            path.closeSubpath()
        return path

    def _paint_rounded(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        radii = self.corner_radii()
        rect = QRectF(self.rect())

        if radii != self._rw_cached_radii or rect != self._rw_cached_rect:
            self._rw_cached_path = self._build_path(rect, *radii)
            self._rw_cached_radii = radii
            self._rw_cached_rect = rect

        brush = self._bg_brush()
        painter.setClipPath(self._rw_cached_path)

        if isinstance(brush, QLinearGradient):
            w, h = self.width(), self.height()
            size = (w, h)
            if self._rw_cached_grad_pm is None or self._rw_cached_grad_size != size:
                brush.setSpread(QLinearGradient.Spread.PadSpread)
                self._rw_cached_grad_pm = _dithered_gradient(w, h, brush)
                self._rw_cached_grad_size = size
            painter.drawPixmap(0, 0, self._rw_cached_grad_pm)
        else:
            painter.fillPath(self._rw_cached_path, brush)

        painter.setClipping(False)

        border = self._border_color()
        if border:
            painter.setPen(QPen(border, 1))
            painter.drawPath(self._rw_cached_path)

        painter.end()
