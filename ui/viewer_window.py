import os
import random
import qtawesome as qta
from PyQt6.QtWidgets import (QWidget, QLabel, QPushButton, QGraphicsOpacityEffect,
                              QGraphicsDropShadowEffect, QApplication)
from PyQt6.QtGui import QPixmap, QColor, QPainter, QIcon, QTransform, QImage, QFont, QFontMetrics
from PyQt6.QtCore import (Qt, QTimer, QPoint, QSize, QRect, QPropertyAnimation,
                           QEasingCurve)
from core.timer_logic import format_time, auto_warn_seconds
from ui.icons import Icons
from ui.scales import S
from ui.platform import setup_frameless_native
from ui.resize_cursor import install_resize_cursor_guard
from core.focus_monitor import get_foreground_app

# Native scan codes for physical key positions (layout-independent hotkeys)
import sys as _sys
if _sys.platform == "darwin":
    SC_H = 4   # macOS keycode for H position
    SC_G = 5   # macOS keycode for G position
    SC_R = 15  # macOS keycode for R position
    SC_F = 3   # macOS keycode for F position
    SC_V = 9   # macOS keycode for V position
    SC_P = 35  # macOS keycode for P position
else:
    SC_H = 35  # Windows scan code
    SC_G = 34
    SC_R = 19
    SC_F = 33
    SC_V = 47
    SC_P = 25
FADE_MS = 200
_OWN_PROCESS = os.path.splitext(os.path.basename(_sys.executable))[0].lower()

# Icon colors
CLR_NORMAL = QColor(204, 192, 174, 255)
CLR_HOVER = QColor(204, 192, 174, 200)
CLR_DIM = QColor(204, 192, 174, 100)
CLR_WARNING = QColor(230, 120, 100, 200)
CLR_WHITE = QColor(255, 255, 255, 255)


def _icon(name, color=CLR_NORMAL, size=15):
    """Create QIcon from qtawesome Phosphor icon."""
    return qta.icon(name, color=color)


def _dpi_pixmap(icon, size):
    """Render icon to pixmap at native screen DPI for sharp display."""
    screen = QApplication.primaryScreen()
    ratio = max(screen.devicePixelRatio() if screen else 2.0, 2.0)
    pm = icon.pixmap(QSize(int(size * ratio), int(size * ratio)))
    pm.setDevicePixelRatio(ratio)
    return pm


def _icon_btn(icon_name, size, parent, color=CLR_NORMAL):
    btn = QPushButton(parent)
    btn.setIcon(_icon(icon_name, color))
    btn.setIconSize(QSize(size, size))
    btn.setFixedSize(size + 6, size + 6)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    btn.setStyleSheet("background: transparent; border: none;")
    return btn


class ProgressBar(QWidget):
    """Thin progress bar at bottom of viewer."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._progress = 0.0
        self._warning = False
        self.setFixedHeight(S.VIEWER_PROGRESS_H)

    def set_progress(self, value, warning=False):
        self._progress = max(0.0, min(1.0, value))
        self._warning = warning
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        w, h = self.width(), self.height()
        # Background
        p.fillRect(0, 0, w, h, QColor(36, 30, 24, 150))
        # Fill
        fill_w = int(w * self._progress)
        if fill_w > 0:
            color = CLR_WARNING if self._warning else QColor(74, 125, 116, 150)
            p.fillRect(0, 0, fill_w, h, color)
        p.end()


class _GradientOverlay(QWidget):
    """Transparent widget that draws top/bottom gradients over the image."""

    def paintEvent(self, event):
        p = QPainter(self)
        w, h = self.width(), self.height()
        # Top gradient (25% of height)
        top_h = max(1, h // 4)
        for i in range(top_h):
            alpha = int(200 * (1 - i / top_h) ** 1.2)
            p.fillRect(0, i, w, 1, QColor(18, 14, 10, alpha))
        # Bottom gradient (25% of height)
        bot_h = max(1, h // 4)
        for i in range(bot_h):
            alpha = int(200 * (i / bot_h) ** 1.2)
            p.fillRect(0, h - bot_h + i, w, 1, QColor(18, 14, 10, alpha))
        p.end()


class _GridOverlay(QWidget):
    """Transparent widget that draws rule of thirds grid."""

    def paintEvent(self, event):
        p = QPainter(self)
        p.setPen(QColor(255, 255, 255, 100))
        w, h = self.width(), self.height()
        # Vertical lines at 1/3 and 2/3
        p.drawLine(w // 3, 0, w // 3, h)
        p.drawLine(2 * w // 3, 0, 2 * w // 3, h)
        # Horizontal lines at 1/3 and 2/3
        p.drawLine(0, h // 3, w, h // 3)
        p.drawLine(0, 2 * h // 3, w, 2 * h // 3)
        p.end()


class ViewerWindow(QWidget):
    def __init__(self, images, settings, on_close=None, settings_window=None):
        super().__init__()
        self.on_close = on_close
        self.settings = settings
        self._settings_window = settings_window
        self._paused = False
        self._was_paused_by_help = False
        self._help_overlay = None
        self._countdown = 0
        self._total_time = 0
        self._drag_pos = None
        self._resize_corner = None
        self._resize_start_pos = None
        self._resize_start_geom = None
        self._aspect = 1.0
        self._pixmap = None
        self._controls_visible = False
        self._is_warning = False
        self._session_limit = settings.get("session_limit")  # seconds or None
        self._session_elapsed = 0
        self._focus_app = settings.get("focus_app")
        self._focus_enabled = settings.get("focus_enabled", False)
        self._grayscale = False
        self._flip_h = False
        self._flip_v = False
        self._grid_thirds = False
        self._topmost = bool(settings.get("topmost"))
        self._cached_label_widths = None
        self._current_scale = 1.0
        self._current_font_timer = S.FONT_TIMER
        self._current_font_counter = S.FONT_COUNTER
        self._current_icon_px = 24
        self._current_btn_icon = 20

        # Window flags
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window
        if self._topmost:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setWindowTitle("Drawer")
        self.setWindowIcon(QIcon(os.path.join(os.path.dirname(__file__), "..", "drawer.ico")))
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("background-color: black;")
        self.setMouseTracking(True)
        self.setMinimumSize(S.VIEWER_MIN_W, S.VIEWER_MIN_H)

        # Build play order
        order = list(range(len(images)))
        if settings.get("order") == "random":
            random.shuffle(order)
        self._play_order = order
        self._images = images
        self._current_idx = 0

        # Image label
        self._img_label = QLabel(self)
        self._img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._img_label.setStyleSheet("background-color: black;")
        self._img_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        # Grid overlay (rule of thirds)
        self._grid_overlay = _GridOverlay(self)
        self._grid_overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._grid_overlay.hide()

        # Gradient overlay (above image, below controls)
        self._gradient = _GradientOverlay(self)
        self._gradient.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._gradient.hide()

        # ---- Hover overlays (fade in/out) ----

        # Top bar
        self._top_left = QWidget(self)
        self._top_left.setStyleSheet("background: transparent;")
        self._info_btn = _icon_btn(Icons.INFO, 20, self._top_left)
        self._info_btn.clicked.connect(self._show_help)
        self._info_btn.move(0, 0)

        # Top center: viewer tools
        self._top_center = QWidget(self)
        self._top_center.setStyleSheet("background: transparent;")
        self._bw_btn = _icon_btn(Icons.BW_OFF, 20, self._top_center)
        self._bw_btn.clicked.connect(self._toggle_grayscale)
        self._grid_btn = _icon_btn(Icons.GRID_OVERLAY, 20, self._top_center)
        self._grid_btn.clicked.connect(self._toggle_grid)
        self._fliph_btn = _icon_btn(Icons.FLIP_H, 20, self._top_center)
        self._fliph_btn.clicked.connect(self._toggle_flip_h)
        self._flipv_btn = _icon_btn(Icons.FLIP_V, 20, self._top_center)
        self._flipv_btn.clicked.connect(self._toggle_flip_v)
        pin_icon = Icons.TOPMOST_ON if self._topmost else Icons.TOPMOST_OFF
        pin_color = CLR_NORMAL if self._topmost else CLR_DIM
        self._pin_btn = _icon_btn(pin_icon, 20, self._top_center, color=pin_color)
        self._pin_btn.clicked.connect(self._toggle_topmost)

        self._top_right = QWidget(self)
        self._top_right.setStyleSheet("background: transparent;")
        self._close_btn = _icon_btn(Icons.CLOSE, 20, self._top_right)
        self._close_btn.clicked.connect(self.close)

        # Center play/pause
        self._center_btn = QPushButton(self)
        self._center_btn.setFixedSize(S.VIEWER_CENTER_BTN, S.VIEWER_CENTER_BTN)
        self._center_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._center_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._center_btn.setStyleSheet("background: transparent; border: none;")
        self._center_btn.setIconSize(QSize(40, 40))
        self._center_btn.clicked.connect(self._toggle_pause)
        self._update_center_icon()

        # Bottom: timer + counter
        self._timer_label = QLabel(self)
        self._timer_label.setStyleSheet(
            f"color: rgba(204,192,174,255); font-family: Lora; font-size: {S.FONT_TIMER}px; background: transparent;")
        self._timer_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self._counter_label = QLabel(self)
        self._counter_label.setStyleSheet(
            f"color: rgba(204,192,174,200); font-family: 'Lexend'; font-size: {S.FONT_COUNTER}px; background: transparent;")
        self._counter_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        # Alarm icon (session warning)
        self._alarm_label = QLabel(self)
        self._alarm_label.setPixmap(
            _dpi_pixmap(_icon(Icons.ALARM, CLR_WARNING), 24))
        self._alarm_label.setFixedSize(S.VIEWER_ICON_LABEL, S.VIEWER_ICON_LABEL)
        self._alarm_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._alarm_label.setStyleSheet("background: transparent;")
        self._alarm_label.hide()

        # Coffee icon (always visible when paused) — drop shadow for visibility on light images
        self._coffee_label = QLabel(self)
        self._coffee_label.setPixmap(
            _dpi_pixmap(_icon(Icons.COFFEE, CLR_WHITE), 24))
        self._coffee_label.setFixedSize(S.VIEWER_ICON_LABEL, S.VIEWER_ICON_LABEL)
        self._coffee_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._coffee_label.setStyleSheet("background: transparent;")
        _shadow = QGraphicsDropShadowEffect(self._coffee_label)
        _shadow.setBlurRadius(35)
        _shadow.setOffset(0, 0)
        _shadow.setColor(QColor(0, 0, 0, 200))
        self._coffee_label.setGraphicsEffect(_shadow)
        self._coffee_label.hide()

        # Progress bar — only visible when session limit is set
        self._progress_bar = ProgressBar(self)
        if not self._session_limit:
            self._progress_bar.hide()

        # Collect hover-only widgets
        self._hover_widgets = [
            self._top_left, self._top_center, self._top_right, self._center_btn,
            self._timer_label, self._counter_label,
            self._progress_bar,
        ]

        # Setup opacity effects for fade
        self._opacity_effects = []
        for w in self._hover_widgets:
            effect = QGraphicsOpacityEffect(w)
            effect.setOpacity(0.0)
            w.setGraphicsEffect(effect)
            self._opacity_effects.append(effect)

        # Timer
        self._qtimer = QTimer(self)
        self._qtimer.setInterval(1000)
        self._qtimer.timeout.connect(self._tick)

        # Debounce timer: switch from fast→smooth image scaling after resize stops
        self._smooth_timer = QTimer(self)
        self._smooth_timer.setSingleShot(True)
        self._smooth_timer.setInterval(150)
        self._smooth_timer.timeout.connect(self._update_display)

        # Focus polling timer (checks foreground window every 500ms)
        self._focus_timer = QTimer(self)
        self._focus_timer.setInterval(500)
        self._focus_timer.timeout.connect(self._check_focus)
        if self._focus_enabled and self._focus_app:
            self._focus_timer.start()

        # Screen limits
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
        install_resize_cursor_guard(self)

    # ------------------------------------------------------------------ Icons

    def _update_center_icon(self):
        if self._paused:
            self._center_btn.setIcon(_icon("ph.play-fill", CLR_HOVER, 40))
        else:
            self._center_btn.setIcon(_icon("ph.pause-fill", CLR_HOVER, 40))

    def _update_coffee(self):
        if self._paused:
            self._coffee_label.setPixmap(
                _dpi_pixmap(_icon(Icons.COFFEE, CLR_WHITE), self._current_icon_px))
            icon_lbl = max(16, round(S.VIEWER_ICON_LABEL * self._current_scale))
            self._coffee_label.setFixedSize(icon_lbl, icon_lbl)
            self._coffee_label.show()
        else:
            self._coffee_label.hide()
        self._layout_bottom(self.width(), self.height())

    def _layout_bottom(self, w, h):
        sc = self._current_scale
        lbl_h = max(16, round(S.VIEWER_BOTTOM_LABEL_H * sc))
        bottom_offset = max(4, round(S.VIEWER_BOTTOM_OFFSET * sc))
        bottom_lbl_x = max(6, round(S.VIEWER_BOTTOM_LABEL_X * sc))
        icon_lbl = max(16, round(S.VIEWER_ICON_LABEL * sc))
        icon_spacing = max(20, round(S.VIEWER_BOTTOM_ICON_SPACING * sc))
        icon_y_offset = round(S.VIEWER_BOTTOM_ICON_Y_OFFSET * sc)

        bottom_y = h - lbl_h - bottom_offset
        x = bottom_lbl_x
        if self._alarm_label.isVisible():
            self._alarm_label.setFixedSize(icon_lbl, icon_lbl)
            self._alarm_label.move(x, bottom_y + icon_y_offset)
            x += icon_spacing
        if self._coffee_label.isVisible():
            self._coffee_label.setFixedSize(icon_lbl, icon_lbl)
            self._coffee_label.move(x, bottom_y + icon_y_offset)
            x += icon_spacing

        # Center timer
        timer_w, counter_w = self._label_widths()
        self._timer_label.setGeometry((w - timer_w) // 2, bottom_y, timer_w, lbl_h)
        self._timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._counter_label.setGeometry(
            w - counter_w - bottom_lbl_x, bottom_y, counter_w, lbl_h)
        self._counter_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    def _label_widths(self):
        """Compute timer and counter label widths from font metrics.
        Cached and invalidated when font sizes change due to window scaling."""
        if self._cached_label_widths is None:
            ft = self._current_font_timer
            fc = self._current_font_counter
            timer_font = QFont("Lora")
            timer_font.setPixelSize(ft)
            timer_w = QFontMetrics(timer_font).horizontalAdvance("0:00:00") + ft // 2

            counter_font = QFont("Lexend")
            counter_font.setPixelSize(fc)
            counter_w = QFontMetrics(counter_font).horizontalAdvance("9999/9999") + fc // 2

            self._cached_label_widths = (timer_w, counter_w)
        return self._cached_label_widths

    # ------------------------------------------------------------------ Image display

    def _show_current_image(self):
        if not self._play_order:
            self._finish()
            return
        img_idx = self._play_order[self._current_idx]
        img = self._images[img_idx]
        pix = QPixmap(img.path)
        if pix.isNull():
            self._advance()
            return
        self._pixmap = pix
        self._aspect = pix.width() / pix.height() if pix.height() else 1.0

        w = self.width()
        h = max(S.VIEWER_MIN_H, int(w / self._aspect))
        if h > self._screen_max_h:
            h = self._screen_max_h
            w = max(S.VIEWER_MIN_W, int(h * self._aspect))
        if w > self._screen_max_w:
            w = self._screen_max_w
            h = max(S.VIEWER_MIN_H, int(w / self._aspect))
        self.resize(w, h)

        self._update_display()
        self._schedule_next(img.timer)
        self._update_counter()
        self._update_session_display()

    def _update_display(self, fast=False):
        if self._pixmap is None:
            return
        pix = self._pixmap
        # Flip
        if self._flip_h or self._flip_v:
            sx = -1 if self._flip_h else 1
            sy = -1 if self._flip_v else 1
            pix = pix.transformed(QTransform().scale(sx, sy))
        # Grayscale
        if self._grayscale:
            img = pix.toImage().convertToFormat(QImage.Format.Format_Grayscale8)
            pix = QPixmap.fromImage(img)
        transform = (Qt.TransformationMode.FastTransformation if fast
                     else Qt.TransformationMode.SmoothTransformation)
        scaled = pix.scaled(
            self._img_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            transform,
        )
        self._img_label.setPixmap(scaled)

    # ------------------------------------------------------------------ Timer

    def _schedule_next(self, seconds):
        self._qtimer.stop()
        self._countdown = seconds
        self._total_time = seconds
        self._update_timer_display()
        if not self._paused:
            self._qtimer.start()

    def _tick(self):
        if self._paused:
            return
        self._countdown -= 1
        self._session_elapsed += 1
        self._update_timer_display()
        self._update_session_display()
        if self._session_limit and self._session_elapsed >= self._session_limit:
            self._finish()
            return
        if self._countdown <= 0:
            self._advance()

    def _update_timer_display(self):
        t = format_time(self._countdown)
        if self._play_order:
            img = self._images[self._play_order[self._current_idx]]
            warn_secs = auto_warn_seconds(img.timer)
        else:
            warn_secs = 0
        self._is_warning = self._countdown <= warn_secs and self._countdown > 0

        idx = self._hover_widgets.index(self._timer_label)
        # Only change color, not font-size (font-size managed by resizeEvent)
        if self._is_warning:
            self._timer_color = "rgba(230,120,100,200)"
            self._opacity_effects[idx].setOpacity(1.0)
        else:
            self._timer_color = "rgba(204,192,174,255)"
            if not self._controls_visible:
                self._opacity_effects[idx].setOpacity(0.0)
        self._timer_label.setStyleSheet(
            f"color: {self._timer_color}; font-family: Lora; font-size: {self._current_font_timer}px; background: transparent;")
        self._timer_label.setText(t)

        self._update_coffee()

    def _update_session_display(self):
        if not self._session_limit:
            self._alarm_label.hide()
            return
        remaining = self._session_limit - self._session_elapsed
        if remaining < 0:
            remaining = 0
        warn_at = min(300, int(self._session_limit * 0.2))
        is_warning = remaining <= warn_at
        if is_warning:
            # Render pixmap at current scale and position before making visible
            icon_lbl = max(16, round(S.VIEWER_ICON_LABEL * self._current_scale))
            self._alarm_label.setFixedSize(icon_lbl, icon_lbl)
            self._alarm_label.setPixmap(
                _dpi_pixmap(_icon(Icons.ALARM, CLR_WARNING), self._current_icon_px))
            self._alarm_label.show()
            self._layout_bottom(self.width(), self.height())
        else:
            self._alarm_label.hide()
        progress = self._session_elapsed / self._session_limit
        self._progress_bar.set_progress(progress, is_warning)
        self._progress_bar.show()

    # ------------------------------------------------------------------ Navigation

    def _advance(self):
        self._current_idx += 1
        if self._current_idx >= len(self._play_order):
            self._finish()
        else:
            self._show_current_image()

    def _next(self):
        self._current_idx = (self._current_idx + 1) % len(self._play_order)
        self._show_current_image()

    def _prev(self):
        self._current_idx = (self._current_idx - 1) % len(self._play_order)
        self._show_current_image()

    def _toggle_pause(self):
        self._paused = not self._paused
        if self._paused:
            self._qtimer.stop()
        else:
            self._qtimer.start()
        self._update_center_icon()
        self._update_coffee()

    def _check_focus(self):
        if not self._focus_enabled or not self._focus_app:
            return
        fg = get_foreground_app()
        if fg is None:
            return
        if fg.lower() == _OWN_PROCESS:
            return
        if fg.lower() != self._focus_app.lower() and not self._paused:
            self._toggle_pause()

    def _dismiss_help(self):
        if self._help_overlay is not None:
            self._help_overlay.deleteLater()
            self._help_overlay = None
            if self._was_paused_by_help:
                self._toggle_pause()

    def _show_help(self):
        if self._help_overlay is not None:
            self._dismiss_help()
            return
        self._was_paused_by_help = not self._paused
        if not self._paused:
            self._toggle_pause()
        from PyQt6.QtWidgets import QScrollArea, QVBoxLayout
        

        self.unsetCursor()
        self._help_overlay = QWidget(self)
        self._help_overlay.setGeometry(self.rect())
        self._help_overlay.setCursor(Qt.CursorShape.ArrowCursor)
        self._help_overlay.setStyleSheet(
            "background-color: rgba(0, 0, 0, 210);")
        self._help_overlay.mousePressEvent = lambda e: self._dismiss_help()

        layout = QVBoxLayout(self._help_overlay)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; }"
            "QScrollBar:vertical { width: 4px; background: transparent; }"
            "QScrollBar::handle:vertical { background: rgba(255,255,255,80); }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }")
        scroll.mousePressEvent = lambda e: self._dismiss_help()

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        content.mousePressEvent = lambda e: self._dismiss_help()
        inner = QVBoxLayout(content)
        inner.setContentsMargins(S.VIEWER_HELP_MARGIN, S.VIEWER_HELP_MARGIN, S.VIEWER_HELP_MARGIN, S.VIEWER_HELP_MARGIN)

        info_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "info_viewer.txt")
        try:
            with open(info_path, encoding="utf-8") as f:
                info_text = f.read().replace("\n", "<br>")
        except FileNotFoundError:
            info_text = "H - help"

        lbl = QLabel(info_text)
        # S.FONT_HELP is DPI-scaled, but user_factor tracks the settings
        # window's size — not the viewer's. So on a big viewer the help text
        # stays tiny unless we also scale by current viewer height.
        HEIGHT_PER_FONT_PX = 45  # 600px viewer → ~14px font, 1800px → ~40px
        help_font = max(S.FONT_HELP, round(self.height() / HEIGHT_PER_FONT_PX))
        lbl.setStyleSheet(f"color: rgba(255,255,255,200); font-size: {help_font}px;")
        lbl.setWordWrap(True)
        lbl.mousePressEvent = lambda e: self._dismiss_help()
        inner.addWidget(lbl)
        inner.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll)
        self._help_overlay.show()

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()
        self._update_display()

    def _finish(self):
        self._focus_timer.stop()
        self._qtimer.stop()
        cb = self.on_close
        self.on_close = None
        self.close()
        if cb:
            cb()

    def _update_counter(self):
        total = len(self._play_order)
        current = self._current_idx + 1
        self._counter_label.setText(f"{current}/{total}")

    # ------------------------------------------------------------------ Viewer tools

    def _toggle_grayscale(self):
        self._grayscale = not self._grayscale
        icon_name = Icons.BW_ON if self._grayscale else Icons.BW_OFF
        self._bw_btn.setIcon(_icon(icon_name, CLR_NORMAL))
        self._bw_btn.setIconSize(QSize(self._current_btn_icon, self._current_btn_icon))
        self._update_display()

    def _toggle_grid(self):
        self._grid_thirds = not self._grid_thirds
        if self._grid_thirds:
            self._grid_overlay.show()
            self._grid_overlay.raise_()
        else:
            self._grid_overlay.hide()

    def _toggle_flip_h(self):
        self._flip_h = not self._flip_h
        self._update_display()

    def _toggle_flip_v(self):
        self._flip_v = not self._flip_v
        self._update_display()

    def _toggle_topmost(self):
        self._topmost = not self._topmost
        flags = self.windowFlags()
        if self._topmost:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()
        icon_name = Icons.TOPMOST_ON if self._topmost else Icons.TOPMOST_OFF
        color = CLR_NORMAL if self._topmost else CLR_DIM
        self._pin_btn.setIcon(_icon(icon_name, color))
        self._pin_btn.setIconSize(QSize(self._current_btn_icon, self._current_btn_icon))

    # ------------------------------------------------------------------ Fade animation

    def _fade_controls(self, show):
        self._controls_visible = show
        target = 1.0 if show else 0.0
        for i, effect in enumerate(self._opacity_effects):
            widget = self._hover_widgets[i]
            # Skip timer if warning (always visible)
            if not show and widget == self._timer_label and self._is_warning:
                continue
            try:
                anim = QPropertyAnimation(effect, b"opacity", self)
                anim.setDuration(FADE_MS)
                anim.setStartValue(effect.opacity())
                anim.setEndValue(target)
                anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
                anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
            except RuntimeError:
                pass

    # ------------------------------------------------------------------ Events

    def keyPressEvent(self, event):
        # Use scan codes for letter keys so hotkeys work on any keyboard layout
        sc = event.nativeScanCode()
        # Help overlay is modal: only Escape and H dismiss it; eat every
        # other key so the user can't pause/seek/etc while reading help.
        if self._help_overlay is not None:
            if event.key() == Qt.Key.Key_Escape or sc == SC_H:
                self._dismiss_help()
            return
        if event.key() == Qt.Key.Key_F11:
            self._toggle_fullscreen()
        elif event.key() == Qt.Key.Key_Escape:
            # Don't toggle on auto-repeat: a long Escape press that just
            # dismissed help would otherwise trip the fullscreen exit on
            # the next repeat event.
            if self.isFullScreen() and not event.isAutoRepeat():
                self._toggle_fullscreen()
        elif event.key() == Qt.Key.Key_Space:
            self._toggle_pause()
        elif event.key() == Qt.Key.Key_Left:
            self._prev()
        elif event.key() == Qt.Key.Key_Right:
            self._next()
        elif sc == SC_H:
            self._show_help()
        elif sc == SC_G:
            self._toggle_grayscale()
        elif sc == SC_R:
            self._toggle_grid()
        elif sc == SC_F:
            self._toggle_flip_h()
        elif sc == SC_V:
            self._toggle_flip_v()
        elif sc == SC_P:
            self._toggle_topmost()
        else:
            super().keyPressEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        if not getattr(self, '_native_setup_done', False):
            self._native_setup_done = True
            setup_frameless_native(self)

    def closeEvent(self, event):
        self._focus_timer.stop()
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
        self._grid_overlay.setGeometry(0, 0, w, h)
        self._gradient.setGeometry(0, 0, w, h)

        # Scale factor based on window height; 450px = 1.0 reference
        scale = max(0.5, min(2.5, h / 450.0))
        self._current_scale = scale

        btn_sz = max(16, round(S.VIEWER_ICON_BTN * scale))
        btn_icon = max(10, btn_sz - 6)
        self._current_btn_icon = btn_icon
        margin = max(4, round(S.VIEWER_ICON_MARGIN * scale))
        gap = max(2, round(S.VIEWER_ICON_GAP * scale))
        center_sz = max(30, round(S.VIEWER_CENTER_BTN * scale))
        progress_h = max(2, round(S.VIEWER_PROGRESS_H * scale))

        # Hide all controls when window is too small to be useful
        controls_visible = h >= 180
        self._top_left.setVisible(controls_visible)
        self._top_right.setVisible(controls_visible)
        if not controls_visible:
            self._top_center.hide()

        # Resize all top-bar icon buttons
        for btn in [self._info_btn, self._close_btn, self._bw_btn, self._grid_btn,
                    self._fliph_btn, self._flipv_btn, self._pin_btn]:
            btn.setFixedSize(btn_sz, btn_sz)
            btn.setIconSize(QSize(btn_icon, btn_icon))

        # Center play/pause button
        self._center_btn.setFixedSize(center_sz, center_sz)
        self._center_btn.setIconSize(QSize(round(center_sz * 0.65), round(center_sz * 0.65)))

        # Font sizes — invalidate label width cache when they change
        font_timer = max(10, round(S.FONT_TIMER * scale))
        font_counter = max(8, round(S.FONT_COUNTER * scale))
        if font_timer != self._current_font_timer or font_counter != self._current_font_counter:
            self._current_font_timer = font_timer
            self._current_font_counter = font_counter
            self._cached_label_widths = None
            self._timer_label.setStyleSheet(
                f"color: rgba(204,192,174,255); font-family: Lora; "
                f"font-size: {font_timer}px; background: transparent;")
            self._counter_label.setStyleSheet(
                f"color: rgba(204,192,174,200); font-family: 'Lexend'; "
                f"font-size: {font_counter}px; background: transparent;")

        # Coffee/alarm icon pixmap size
        icon_px = max(12, round(24 * scale))
        if icon_px != self._current_icon_px:
            self._current_icon_px = icon_px
            icon_lbl = max(16, round(S.VIEWER_ICON_LABEL * scale))
            self._alarm_label.setFixedSize(icon_lbl, icon_lbl)
            if self._alarm_label.isVisible():
                self._alarm_label.setPixmap(
                    _dpi_pixmap(_icon(Icons.ALARM, CLR_WARNING), icon_px))
            self._coffee_label.setFixedSize(icon_lbl, icon_lbl)
            if self._coffee_label.isVisible():
                self._coffee_label.setPixmap(
                    _dpi_pixmap(_icon(Icons.COFFEE, CLR_WHITE), icon_px))

        # Top left: info
        self._top_left.setGeometry(margin, margin, btn_sz, btn_sz)
        self._info_btn.setGeometry(0, 0, btn_sz, btn_sz)

        # Top right: close
        tr_x = w - btn_sz - margin
        self._top_right.setGeometry(tr_x, margin, btn_sz, btn_sz)
        self._close_btn.setGeometry(0, 0, btn_sz, btn_sz)

        # Viewer tools — reflow based on available space:
        # 1) horizontal at top if wide enough
        # 2) vertical column on left if tall enough
        # 3) hide if too small (keyboard shortcuts still work)
        tl_right = margin + btn_sz + gap
        all_btns = [self._bw_btn, self._grid_btn,
                    self._fliph_btn, self._flipv_btn, self._pin_btn]
        n = len(all_btns)
        tc_w = btn_sz * n + gap * (n - 1)
        fits_horizontal = tl_right + tc_w + gap + btn_sz <= w - margin
        col_h = btn_sz * n + gap * (n - 1)
        col_y = margin + btn_sz + gap
        fits_vertical = col_y + col_h < (h - center_sz) // 2

        if fits_horizontal:
            self._top_center.show()
            for btn in all_btns:
                btn.show()
            tc_x = (w - tc_w) // 2
            if tc_x < tl_right:
                tc_x = tl_right
            self._top_center.setGeometry(tc_x, margin, tc_w, btn_sz)
            for i, btn in enumerate(all_btns):
                btn.setGeometry(i * (btn_sz + gap), 0, btn_sz, btn_sz)
        elif fits_vertical:
            self._top_center.show()
            for btn in all_btns:
                btn.show()
            self._top_center.setGeometry(margin, col_y, btn_sz, col_h)
            for i, btn in enumerate(all_btns):
                btn.setGeometry(0, i * (btn_sz + gap), btn_sz, btn_sz)
        else:
            self._top_center.hide()

        # Center
        self._center_btn.move((w - center_sz) // 2, (h - center_sz) // 2)

        # Bottom layout
        self._layout_bottom(w, h)

        # Progress bar at very bottom
        self._progress_bar.setFixedHeight(progress_h)
        self._progress_bar.setGeometry(0, h - progress_h, w, progress_h)

        # Fast render during drag; smooth render fires after resize stops
        self._update_display(fast=True)
        self._smooth_timer.start()

    def enterEvent(self, event):
        super().enterEvent(event)
        self._gradient.show()
        self._gradient.raise_()
        # Raise all controls above gradient
        for w in self._hover_widgets:
            w.raise_()
        self._coffee_label.raise_()
        self._alarm_label.raise_()
        self._fade_controls(True)
        # Keep the help overlay on top of any controls we just re-raised,
        # otherwise clicks land on the underlying buttons and the user can
        # play/pause while reading help.
        if self._help_overlay is not None:
            self._help_overlay.raise_()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self._gradient.hide()
        self._fade_controls(False)
        if not self._resize_corner:
            self.unsetCursor()

    # ------------------------------------------------------------------ Mouse handling

    def mousePressEvent(self, event):
        pos = event.position().toPoint()
        if event.button() == Qt.MouseButton.RightButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        elif event.button() == Qt.MouseButton.LeftButton:
            corner = self._get_corner(pos)
            if corner:
                self._resize_corner = corner
                self._resize_start_pos = event.globalPosition().toPoint()
                self._resize_start_geom = self.geometry()
                event.accept()
            elif pos.x() < S.VIEWER_NAV_ZONE and self._controls_visible:
                self._prev()
                event.accept()
            elif pos.x() > self.width() - S.VIEWER_NAV_ZONE and self._controls_visible:
                self._next()
                event.accept()
            else:
                event.ignore()

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()
        # Don't show resize cursor over interactive buttons
        if not self._resize_corner and self._controls_visible:
            child = self.childAt(pos)
            if isinstance(child, QPushButton):
                self.unsetCursor()
                corner = None
            else:
                corner = self._get_corner(pos, cursor_only=True)
                self._update_cursor(corner)
        else:
            corner = self._get_corner(pos, cursor_only=True)
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

    def _get_corner(self, pos, cursor_only=False):
        w, h = self.width(), self.height()
        x, y = pos.x(), pos.y()
        edge = S.RESIZE_CURSOR_W if cursor_only else S.RESIZE_GRIP_W
        g = S.VIEWER_CORNER_GRIP
        in_left = x < g
        in_right = x > w - g
        in_top = y < g
        in_bottom = y > h - g
        if in_top and in_left:
            return "tl"
        if in_top and in_right:
            return "tr"
        if in_bottom and in_left:
            return "bl"
        if in_bottom and in_right:
            return "br"
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
            new_w = min(self._screen_max_w, max(S.VIEWER_MIN_W, geom.width() + dx))
            new_h = min(self._screen_max_h, max(S.VIEWER_MIN_H, int(new_w / self._aspect)))
            self.setGeometry(geom.x(), geom.y(), new_w, new_h)
        elif corner in ("bl", "l"):
            new_w = min(self._screen_max_w, max(S.VIEWER_MIN_W, geom.width() - dx))
            new_h = min(self._screen_max_h, max(S.VIEWER_MIN_H, int(new_w / self._aspect)))
            new_x = geom.right() - new_w
            self.setGeometry(new_x, geom.y(), new_w, new_h)
        elif corner in ("tr",):
            new_w = min(self._screen_max_w, max(S.VIEWER_MIN_W, geom.width() + dx))
            new_h = min(self._screen_max_h, max(S.VIEWER_MIN_H, int(new_w / self._aspect)))
            new_y = geom.bottom() - new_h
            self.setGeometry(geom.x(), new_y, new_w, new_h)
        elif corner in ("tl", "t"):
            new_w = min(self._screen_max_w, max(S.VIEWER_MIN_W, geom.width() - dx))
            new_h = min(self._screen_max_h, max(S.VIEWER_MIN_H, int(new_w / self._aspect)))
            new_x = geom.right() - new_w
            new_y = geom.bottom() - new_h
            self.setGeometry(new_x, new_y, new_w, new_h)
