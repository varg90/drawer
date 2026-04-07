import random
from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QPushButton, QVBoxLayout
from PyQt6.QtGui import QPixmap, QCursor, QColor, QPainter, QFont, QPen, QPolygonF
from PyQt6.QtCore import Qt, QTimer, QPoint, QSize, QRect, QPointF
from core.timer_logic import format_time, auto_warn_seconds

CORNER_GRIP = 50  # pixels from corner to trigger resize
CONTROLS_HEIGHT = 48
COUNTER_HEIGHT = 28
MIN_WIDTH = 200
MIN_HEIGHT = 150


class IconButton(QPushButton):
    """Minimalist painted icon button."""

    def __init__(self, icon_type, size=28, parent=None):
        super().__init__(parent)
        self._icon_type = icon_type
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setStyleSheet("background: transparent; border: none;")
        self._hovered = False

    def set_icon_type(self, icon_type):
        self._icon_type = icon_type
        self.update()

    def enterEvent(self, event):
        self._hovered = True
        self.update()

    def leaveEvent(self, event):
        self._hovered = False
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        alpha = 220 if self._hovered else 140
        color = QColor(255, 255, 255, alpha)
        p.setPen(QPen(color, 1.5))
        p.setBrush(color)

        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        s = min(w, h) * 0.32  # scale

        if self._icon_type == "prev":
            # |◁  — bar + triangle
            p.drawLine(QPointF(cx - s, cy - s), QPointF(cx - s, cy + s))
            tri = QPolygonF([QPointF(cx + s, cy - s), QPointF(cx - s * 0.3, cy), QPointF(cx + s, cy + s)])
            p.drawPolygon(tri)

        elif self._icon_type == "next":
            # ▷|  — triangle + bar
            p.drawLine(QPointF(cx + s, cy - s), QPointF(cx + s, cy + s))
            tri = QPolygonF([QPointF(cx - s, cy - s), QPointF(cx + s * 0.3, cy), QPointF(cx - s, cy + s)])
            p.drawPolygon(tri)

        elif self._icon_type == "pause":
            # ||  — two bars
            bw = s * 0.3
            p.drawRect(QRect(int(cx - s), int(cy - s), int(bw), int(s * 2)))
            p.drawRect(QRect(int(cx + s - bw), int(cy - s), int(bw), int(s * 2)))

        elif self._icon_type == "play":
            # ▶  — triangle
            tri = QPolygonF([QPointF(cx - s * 0.7, cy - s), QPointF(cx + s, cy), QPointF(cx - s * 0.7, cy + s)])
            p.drawPolygon(tri)

        elif self._icon_type == "settings":
            # ☰  — three horizontal lines
            p.setPen(QPen(color, 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            for dy in [-s * 0.7, 0, s * 0.7]:
                p.drawLine(QPointF(cx - s, cy + dy), QPointF(cx + s, cy + dy))

        elif self._icon_type == "help":
            # ?  — question mark
            p.setPen(QPen(color, 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            font = p.font()
            font.setPixelSize(int(s * 2.2))
            font.setBold(True)
            p.setFont(font)
            p.drawText(QRect(0, 0, w, h), Qt.AlignmentFlag.AlignCenter, "?")

        elif self._icon_type == "fullscreen":
            # ⛶  — four corners
            p.setPen(QPen(color, 1.5))
            p.setBrush(Qt.BrushStyle.NoBrush)
            d = s * 0.9
            c = s * 0.4
            for dx, dy in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
                ox, oy = cx + dx * d, cy + dy * d
                p.drawLine(QPointF(ox, oy), QPointF(ox - dx * c, oy))
                p.drawLine(QPointF(ox, oy), QPointF(ox, oy - dy * c))

        elif self._icon_type == "exitfullscreen":
            # Inward corners
            p.setPen(QPen(color, 1.5))
            p.setBrush(Qt.BrushStyle.NoBrush)
            d = s * 0.4
            c = s * 0.4
            for dx, dy in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
                ox, oy = cx + dx * d, cy + dy * d
                p.drawLine(QPointF(ox, oy), QPointF(ox + dx * c, oy))
                p.drawLine(QPointF(ox, oy), QPointF(ox, oy + dy * c))

        elif self._icon_type == "close":
            # ×  — cross
            p.setPen(QPen(color, 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawLine(QPointF(cx - s * 0.7, cy - s * 0.7), QPointF(cx + s * 0.7, cy + s * 0.7))
            p.drawLine(QPointF(cx + s * 0.7, cy - s * 0.7), QPointF(cx - s * 0.7, cy + s * 0.7))

        p.end()


class ViewerWindow(QWidget):
    def __init__(self, images, settings, on_close=None):
        super().__init__()
        self.on_close = on_close
        self.settings = settings
        self._paused = False
        self._countdown = 0
        self._drag_pos = None
        self._resize_corner = None
        self._resize_start_pos = None
        self._resize_start_geom = None
        self._aspect = 1.0
        self._pixmap = None
        self._controls_visible = False

        # Window flags
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window
        if settings.get("topmost"):
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("background-color: black;")
        self.setMouseTracking(True)
        self.setMinimumSize(MIN_WIDTH, MIN_HEIGHT)

        # Build play order
        order = list(range(len(images)))
        if settings.get("order") == "random":
            random.shuffle(order)
        self._play_order = order
        self._images = images
        self._current_idx = 0  # index into _play_order

        # Image display label
        self._img_label = QLabel(self)
        self._img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._img_label.setStyleSheet("background-color: black;")
        self._img_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._img_label.setGeometry(self.rect())

        # Bottom nav bar — centered at bottom
        self._controls_bar = QWidget(self)
        self._controls_bar.setStyleSheet(
            "background-color: rgba(20, 20, 20, 180);"
        )
        ctrl_layout = QHBoxLayout(self._controls_bar)
        ctrl_layout.setContentsMargins(10, 4, 10, 4)
        ctrl_layout.setSpacing(4)

        self._prev_btn = IconButton("prev", 28, self._controls_bar)
        self._prev_btn.clicked.connect(self._prev)
        ctrl_layout.addWidget(self._prev_btn)

        self._pause_btn = IconButton("pause", 28, self._controls_bar)
        self._pause_btn.clicked.connect(self._toggle_pause)
        ctrl_layout.addWidget(self._pause_btn)

        self._next_btn = IconButton("next", 28, self._controls_bar)
        self._next_btn.clicked.connect(self._next)
        ctrl_layout.addWidget(self._next_btn)

        self._timer_label = QLabel("")
        self._timer_label.setStyleSheet(
            "color: rgba(255,255,255,160); font-size: 13px; background: transparent;")
        ctrl_layout.addWidget(self._timer_label)

        self._controls_bar.adjustSize()
        self._controls_bar.hide()

        # Top-right buttons
        self._top_buttons = QWidget(self)
        self._top_buttons.setStyleSheet(
            "background-color: rgba(20, 20, 20, 180);"
        )
        top_layout = QHBoxLayout(self._top_buttons)
        top_layout.setContentsMargins(4, 2, 4, 2)
        top_layout.setSpacing(2)

        self._help_btn = IconButton("help", 24, self._top_buttons)
        self._help_btn.setToolTip("Горячие клавиши")
        self._help_btn.clicked.connect(self._show_help)
        top_layout.addWidget(self._help_btn)

        self._fullscreen_btn = IconButton("fullscreen", 24, self._top_buttons)
        self._fullscreen_btn.setToolTip("На весь экран")
        self._fullscreen_btn.clicked.connect(self._toggle_fullscreen)
        top_layout.addWidget(self._fullscreen_btn)

        self._settings_btn = IconButton("settings", 24, self._top_buttons)
        self._settings_btn.setToolTip("Настройки")
        self._settings_btn.clicked.connect(self._open_settings)
        top_layout.addWidget(self._settings_btn)

        self._close_btn = IconButton("close", 24, self._top_buttons)
        self._close_btn.setToolTip("Закрыть")
        self._close_btn.clicked.connect(self.close)
        top_layout.addWidget(self._close_btn)

        self._top_buttons.adjustSize()
        self._top_buttons.hide()

        # Counter label (bottom)
        self._counter_label = QLabel("")
        self._counter_label.setParent(self)
        self._counter_label.setStyleSheet(
            "color: rgba(200,200,200,180); font-size: 12px; background: transparent;"
        )
        self._counter_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._counter_label.setFixedHeight(COUNTER_HEIGHT)
        self._counter_label.hide()

        # Warn overlay label
        self._warn_label = QLabel("", self)
        self._warn_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._warn_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._warn_label.setStyleSheet(
            "color: rgba(255, 80, 80, 220); font-size: 16px; font-weight: bold; background: transparent;"
        )
        self._warn_label.hide()

        # Timer
        self._qtimer = QTimer(self)
        self._qtimer.setInterval(1000)
        self._qtimer.timeout.connect(self._tick)

        # Show first image — fit within screen
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().availableGeometry()
        self._screen_max_w = screen.width() - 20
        self._screen_max_h = screen.height() - 20
        saved = settings.get("viewer_size")
        if saved and len(saved) == 2:
            self.resize(min(saved[0], self._screen_max_w), min(saved[1], self._screen_max_h))
        else:
            max_w = int(screen.width() * 0.7)
            max_h = int(screen.height() * 0.7)
            self.resize(min(800, max_w), min(600, max_h))
        self._show_current_image()

    # ------------------------------------------------------------------ Image display

    def _show_current_image(self):
        if not self._play_order:
            self._finish()
            return
        img_idx = self._play_order[self._current_idx]
        img = self._images[img_idx]
        pix = QPixmap(img.path)
        if pix.isNull():
            # Skip missing images — try next
            self._advance()
            return
        self._pixmap = pix
        self._aspect = pix.width() / pix.height() if pix.height() else 1.0

        # Resize window to image aspect ratio, fit within screen
        w = self.width()
        h = max(MIN_HEIGHT, int(w / self._aspect))
        if h > self._screen_max_h:
            h = self._screen_max_h
            w = max(MIN_WIDTH, int(h * self._aspect))
        if w > self._screen_max_w:
            w = self._screen_max_w
            h = max(MIN_HEIGHT, int(w / self._aspect))
        self.resize(w, h)

        self._update_display()
        self._schedule_next(img.timer)
        self._update_counter()

    def _update_display(self):
        if self._pixmap is None:
            return
        scaled = self._pixmap.scaled(
            self._img_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._img_label.setPixmap(scaled)

    # ------------------------------------------------------------------ Timer

    def _schedule_next(self, seconds):
        self._qtimer.stop()
        self._countdown = seconds
        self._update_timer_display()
        if not self._paused:
            self._qtimer.start()

    def _tick(self):
        if self._paused:
            return
        self._countdown -= 1
        self._update_timer_display()
        if self._countdown <= 0:
            self._advance()

    def _update_timer_display(self):
        t = format_time(self._countdown)
        warn_secs = auto_warn_seconds(
            self._play_order[self._current_idx]
            if self._play_order else 300
        )
        # Use the current image's timer for warn threshold
        if self._play_order:
            img = self._images[self._play_order[self._current_idx]]
            warn_secs = auto_warn_seconds(img.timer)
        is_warning = self._countdown <= warn_secs
        color = "#ff5555" if is_warning else "white"
        self._timer_label.setStyleSheet(f"color: {color}; font-size: 14px;")
        self._timer_label.setText(t)
        if is_warning and self._countdown > 0:
            self._warn_label.setText(t)
            self._warn_label.show()
        else:
            self._warn_label.hide()

    # ------------------------------------------------------------------ Navigation

    def _advance(self):
        """Auto-advance: does NOT wrap around."""
        self._current_idx += 1
        if self._current_idx >= len(self._play_order):
            self._finish()
        else:
            self._show_current_image()

    def _next(self):
        """Manual next: wraps around."""
        self._current_idx = (self._current_idx + 1) % len(self._play_order)
        self._show_current_image()

    def _prev(self):
        """Manual prev: wraps around."""
        self._current_idx = (self._current_idx - 1) % len(self._play_order)
        self._show_current_image()

    def _toggle_pause(self):
        self._paused = not self._paused
        if self._paused:
            self._qtimer.stop()
            self._pause_btn.set_icon_type("play")
        else:
            self._pause_btn.set_icon_type("pause")
            self._qtimer.start()

    def _show_help(self):
        if hasattr(self, "_help_overlay") and self._help_overlay.isVisible():
            self._help_overlay.hide()
            return
        self._help_overlay = QLabel(self)
        self._help_overlay.setStyleSheet(
            "background-color: rgba(0, 0, 0, 210); color: rgba(255,255,255,200); "
            "font-size: 13px; padding: 20px;")
        self._help_overlay.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._help_overlay.setText(
            "Пробел — пауза / продолжить\n"
            "\u2190  \u2192  — предыдущее / следующее\n"
            "F11 — полный экран\n"
            "Esc — выйти из полного экрана\n"
            "? — эта справка\n\n"
            "ПКМ + перетаскивание — переместить окно\n"
            "Края окна — изменить размер"
        )
        self._help_overlay.setGeometry(self.rect())
        self._help_overlay.show()
        self._help_overlay.mousePressEvent = lambda e: self._help_overlay.hide()

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self._fullscreen_btn.set_icon_type("fullscreen")
            self._fullscreen_btn.setToolTip("На весь экран")
        else:
            self.showFullScreen()
            self._fullscreen_btn.set_icon_type("exitfullscreen")
            self._fullscreen_btn.setToolTip("Выйти из полноэкранного")
        self._update_display()

    def _open_settings(self):
        if not self._paused:
            self._toggle_pause()
        if self.on_close:
            self.on_close(return_only=True)

    def _finish(self):
        self._qtimer.stop()
        cb = self.on_close
        self.on_close = None  # prevent double-call from closeEvent
        self.close()
        if cb:
            cb()

    def _update_counter(self):
        total = len(self._play_order)
        current = self._current_idx + 1
        self._counter_label.setText(f"{current} / {total}")

    # ------------------------------------------------------------------ Events

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F11:
            self._toggle_fullscreen()
        elif event.key() == Qt.Key.Key_Escape and self.isFullScreen():
            self._toggle_fullscreen()
        elif event.key() == Qt.Key.Key_Space:
            self._toggle_pause()
        elif event.key() == Qt.Key.Key_Left:
            self._prev()
        elif event.key() == Qt.Key.Key_Right:
            self._next()
        elif event.key() == Qt.Key.Key_Question or event.key() == Qt.Key.Key_H:
            self._show_help()
        elif event.key() == Qt.Key.Key_Escape:
            if hasattr(self, "_help_overlay") and self._help_overlay.isVisible():
                self._help_overlay.hide()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        self._qtimer.stop()
        if self.on_close:
            cb = self.on_close
            self.on_close = None
            cb()
        event.accept()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w, h = self.width(), self.height()
        self._img_label.setGeometry(0, 0, w, h)
        # Bottom nav bar — centered
        bar_w = self._controls_bar.sizeHint().width()
        bar_h = self._controls_bar.sizeHint().height()
        self._controls_bar.setGeometry((w - bar_w) // 2, h - bar_h - 10, bar_w, bar_h)
        # Top-right buttons
        top_w = self._top_buttons.sizeHint().width()
        top_h = self._top_buttons.sizeHint().height()
        self._top_buttons.setGeometry(w - top_w - 8, 8, top_w, top_h)
        # Counter top-left (offset if warning visible)
        self._counter_label.setGeometry(8, 28, w - 8, COUNTER_HEIGHT)
        # Warning above nav bar
        self._warn_label.setGeometry(8, 4, 120, 30)
        self._update_display()

    def enterEvent(self, event):
        super().enterEvent(event)
        self._show_controls(True)

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self._show_controls(False)

    def _show_controls(self, visible):
        self._controls_visible = visible
        if visible:
            self._controls_bar.show()
            self._top_buttons.show()
            self._counter_label.show()
        else:
            self._controls_bar.hide()
            self._top_buttons.hide()
            self._counter_label.hide()

    # ------------------------------------------------------------------ Mouse handling

    def mousePressEvent(self, event):
        pos = event.position().toPoint()
        if event.button() == Qt.MouseButton.RightButton:
            # Right-drag to move window
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        elif event.button() == Qt.MouseButton.LeftButton:
            corner = self._get_corner(pos)
            if corner:
                self._resize_corner = corner
                self._resize_start_pos = event.globalPosition().toPoint()
                self._resize_start_geom = self.geometry()
                event.accept()
            else:
                event.ignore()

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()
        # Update cursor
        corner = self._get_corner(pos)
        self._update_cursor(corner)

        buttons = event.buttons()
        if buttons & Qt.MouseButton.RightButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
        elif buttons & Qt.MouseButton.LeftButton and self._resize_corner:
            self._do_resize(event.globalPosition().toPoint())
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self._drag_pos = None
        elif event.button() == Qt.MouseButton.LeftButton:
            self._resize_corner = None
            self._resize_start_pos = None
            self._resize_start_geom = None
            pos = event.position().toPoint()
            self._update_cursor(self._get_corner(pos))

    def _get_corner(self, pos):
        w, h = self.width(), self.height()
        x, y = pos.x(), pos.y()
        edge = 6
        g = CORNER_GRIP
        in_left = x < g
        in_right = x > w - g
        in_top = y < g
        in_bottom = y > h - g
        # Corners
        if in_top and in_left:
            return "tl"
        if in_top and in_right:
            return "tr"
        if in_bottom and in_left:
            return "bl"
        if in_bottom and in_right:
            return "br"
        # Edges
        if x < edge:
            return "l"
        if x > w - edge:
            return "r"
        if y < edge:
            return "t"
        if y > h - edge:
            return "b"
        return None

    def _update_cursor(self, corner):
        if corner in ("tl", "br"):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif corner in ("tr", "bl"):
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif corner in ("l", "r"):
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif corner in ("t", "b"):
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        else:
            self.unsetCursor()

    def _do_resize(self, global_pos):
        if not self._resize_start_pos or not self._resize_start_geom:
            return
        dx = global_pos.x() - self._resize_start_pos.x()
        dy = global_pos.y() - self._resize_start_pos.y()
        geom = self._resize_start_geom
        corner = self._resize_corner

        if corner in ("br", "r", "b"):
            new_w = max(MIN_WIDTH, geom.width() + dx)
            new_h = max(MIN_HEIGHT, int(new_w / self._aspect))
            self.setGeometry(geom.x(), geom.y(), new_w, new_h)
        elif corner in ("bl", "l"):
            new_w = max(MIN_WIDTH, geom.width() - dx)
            new_h = max(MIN_HEIGHT, int(new_w / self._aspect))
            new_x = geom.right() - new_w
            self.setGeometry(new_x, geom.y(), new_w, new_h)
        elif corner in ("tr",):
            new_w = max(MIN_WIDTH, geom.width() + dx)
            new_h = max(MIN_HEIGHT, int(new_w / self._aspect))
            new_y = geom.bottom() - new_h
            self.setGeometry(geom.x(), new_y, new_w, new_h)
        elif corner in ("tl", "t"):
            new_w = max(MIN_WIDTH, geom.width() - dx)
            new_h = max(MIN_HEIGHT, int(new_w / self._aspect))
            new_x = geom.right() - new_w
            new_y = geom.bottom() - new_h
            self.setGeometry(new_x, new_y, new_w, new_h)
