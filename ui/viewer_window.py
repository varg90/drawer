import random
from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QPushButton, QVBoxLayout
from PyQt6.QtGui import QPixmap, QCursor, QColor, QPainter, QFont
from PyQt6.QtCore import Qt, QTimer, QPoint, QSize, QRect
from core.timer_logic import format_time, auto_warn_seconds

CORNER_GRIP = 50  # pixels from corner to trigger resize
CONTROLS_HEIGHT = 48
COUNTER_HEIGHT = 28
MIN_WIDTH = 200
MIN_HEIGHT = 150


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
        self._img_label.setGeometry(self.rect())

        # Controls overlay (top bar)
        btn_style = """
            QPushButton {
                background: transparent;
                color: #ccc;
                font-size: 16px;
                font-weight: bold;
                border: none;
                padding: 2px 8px;
            }
            QPushButton:hover { color: #fff; }
        """

        # Bottom nav bar — centered at bottom
        self._controls_bar = QWidget(self)
        self._controls_bar.setStyleSheet(
            "background-color: rgba(20, 20, 20, 200);"
        )
        ctrl_layout = QHBoxLayout(self._controls_bar)
        ctrl_layout.setContentsMargins(12, 4, 12, 4)
        ctrl_layout.setSpacing(6)

        self._prev_btn = QPushButton("\u23ee")
        self._prev_btn.setStyleSheet(btn_style)
        self._prev_btn.clicked.connect(self._prev)
        ctrl_layout.addWidget(self._prev_btn)

        self._pause_btn = QPushButton("\u23f8")
        self._pause_btn.setStyleSheet(btn_style)
        self._pause_btn.clicked.connect(self._toggle_pause)
        ctrl_layout.addWidget(self._pause_btn)

        self._next_btn = QPushButton("\u23ed")
        self._next_btn.setStyleSheet(btn_style)
        self._next_btn.clicked.connect(self._next)
        ctrl_layout.addWidget(self._next_btn)

        self._timer_label = QLabel("")
        self._timer_label.setStyleSheet("color: white; font-size: 14px;")
        ctrl_layout.addWidget(self._timer_label)

        self._controls_bar.adjustSize()
        self._controls_bar.hide()

        # Top-right buttons
        self._top_buttons = QWidget(self)
        self._top_buttons.setStyleSheet(
            "background-color: rgba(20, 20, 20, 200);"
        )
        top_layout = QHBoxLayout(self._top_buttons)
        top_layout.setContentsMargins(6, 2, 6, 2)
        top_layout.setSpacing(2)

        self._settings_btn = QPushButton("\u2261")
        self._settings_btn.setStyleSheet(btn_style)
        self._settings_btn.setToolTip("Вернуться к настройкам")
        self._settings_btn.clicked.connect(self._open_settings)
        top_layout.addWidget(self._settings_btn)

        self._close_btn = QPushButton("x")
        self._close_btn.setStyleSheet(btn_style)
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
        max_w = int(screen.width() * 0.7)
        max_h = int(screen.height() * 0.7)
        self.resize(min(800, max_w), min(600, max_h))
        self._screen_max_w = screen.width() - 20
        self._screen_max_h = screen.height() - 20
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
            self._pause_btn.setText("\u25b6")
        else:
            self._pause_btn.setText("\u23f8")
            self._qtimer.start()

    def _open_settings(self):
        self._qtimer.stop()
        if self.on_close:
            self.on_close()
        self.close()

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
        if corner in ("tl", "br"):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif corner in ("tr", "bl"):
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif corner:
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        else:
            self.unsetCursor()

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

    def _get_corner(self, pos):
        w, h = self.width(), self.height()
        x, y = pos.x(), pos.y()
        edge = 8  # edge grab zone
        g = CORNER_GRIP
        in_left = x < g
        in_right = x > w - g
        in_top = y < g
        in_bottom = y > h - g
        # Corners first
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
            return "bl"
        if x > w - edge:
            return "br"
        if y < edge:
            return "tl"
        if y > h - edge:
            return "br"
        return None

    def _do_resize(self, global_pos):
        if not self._resize_start_pos or not self._resize_start_geom:
            return
        dx = global_pos.x() - self._resize_start_pos.x()
        dy = global_pos.y() - self._resize_start_pos.y()
        geom = self._resize_start_geom
        corner = self._resize_corner

        if corner == "br":
            new_w = max(MIN_WIDTH, geom.width() + dx)
            new_h = max(MIN_HEIGHT, int(new_w / self._aspect))
            self.setGeometry(geom.x(), geom.y(), new_w, new_h)
        elif corner == "bl":
            new_w = max(MIN_WIDTH, geom.width() - dx)
            new_h = max(MIN_HEIGHT, int(new_w / self._aspect))
            new_x = geom.right() - new_w
            self.setGeometry(new_x, geom.y(), new_w, new_h)
        elif corner == "tr":
            new_w = max(MIN_WIDTH, geom.width() + dx)
            new_h = max(MIN_HEIGHT, int(new_w / self._aspect))
            new_y = geom.bottom() - new_h
            self.setGeometry(geom.x(), new_y, new_w, new_h)
        elif corner == "tl":
            new_w = max(MIN_WIDTH, geom.width() - dx)
            new_h = max(MIN_HEIGHT, int(new_w / self._aspect))
            new_x = geom.right() - new_w
            new_y = geom.bottom() - new_h
            self.setGeometry(new_x, new_y, new_w, new_h)
