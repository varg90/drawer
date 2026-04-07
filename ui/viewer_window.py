import random
import qtawesome as qta
from PyQt6.QtWidgets import (QWidget, QLabel, QPushButton, QGraphicsOpacityEffect,
                              QApplication)
from PyQt6.QtGui import QPixmap, QColor, QPainter, QIcon
from PyQt6.QtCore import (Qt, QTimer, QPoint, QSize, QRect, QPropertyAnimation,
                           QEasingCurve)
from core.timer_logic import format_time, auto_warn_seconds

CORNER_GRIP = 50
MIN_WIDTH = 200
MIN_HEIGHT = 150
NAV_ZONE = 40  # side click zone width
FADE_MS = 200

# Icon colors
CLR_NORMAL = QColor(255, 255, 255, 115)
CLR_HOVER = QColor(255, 255, 255, 180)
CLR_DIM = QColor(255, 255, 255, 75)
CLR_WARNING = QColor(255, 85, 85, 200)


def _icon(name, color=CLR_NORMAL, size=15):
    """Create QIcon from qtawesome Phosphor icon."""
    return qta.icon(name, color=color)


def _icon_btn(icon_name, size, parent, color=CLR_NORMAL, tooltip=""):
    btn = QPushButton(parent)
    btn.setIcon(_icon(icon_name, color))
    btn.setIconSize(QSize(size, size))
    btn.setFixedSize(size + 6, size + 6)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    btn.setStyleSheet("background: transparent; border: none;")
    if tooltip:
        btn.setToolTip(tooltip)
    return btn


class ProgressBar(QWidget):
    """Thin progress bar at bottom of viewer."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._progress = 0.0
        self._warning = False
        self.setFixedHeight(3)

    def set_progress(self, value, warning=False):
        self._progress = max(0.0, min(1.0, value))
        self._warning = warning
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        w, h = self.width(), self.height()
        # Background
        p.fillRect(0, 0, w, h, QColor(255, 255, 255, 20))
        # Fill
        fill_w = int(w * self._progress)
        if fill_w > 0:
            color = QColor(255, 85, 85, 200) if self._warning else QColor(255, 255, 255, 90)
            p.fillRect(0, 0, fill_w, h, color)
        p.end()


class _GradientOverlay(QWidget):
    """Transparent widget that draws top/bottom gradients over the image."""

    def paintEvent(self, event):
        p = QPainter(self)
        w, h = self.width(), self.height()
        # Top gradient
        top_h = min(80, h // 3)
        for i in range(top_h):
            alpha = int(200 * (1 - i / top_h) ** 1.2)
            p.fillRect(0, i, w, 1, QColor(0, 0, 0, alpha))
        # Bottom gradient
        bot_h = min(70, h // 3)
        for i in range(bot_h):
            alpha = int(180 * (i / bot_h) ** 1.2)
            p.fillRect(0, h - bot_h + i, w, 1, QColor(0, 0, 0, alpha))
        p.end()


class ViewerWindow(QWidget):
    def __init__(self, images, settings, on_close=None):
        super().__init__()
        self.on_close = on_close
        self.settings = settings
        self._paused = False
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
        self._current_idx = 0

        # Image label
        self._img_label = QLabel(self)
        self._img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._img_label.setStyleSheet("background-color: black;")
        self._img_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        # Gradient overlay (above image, below controls)
        self._gradient = _GradientOverlay(self)
        self._gradient.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._gradient.hide()

        # ---- Hover overlays (fade in/out) ----

        # Top bar (gradient drawn in paintEvent)
        self._top_left = QWidget(self)
        self._top_left.setStyleSheet("background: transparent;")
        self._info_btn = _icon_btn("ph.info-light", 20, self._top_left, tooltip="Инфо")
        self._info_btn.clicked.connect(self._show_help)
        self._info_btn.move(0, 0)

        self._top_right = QWidget(self)
        self._top_right.setStyleSheet("background: transparent;")
        self._settings_btn = _icon_btn("ph.dots-three-vertical-light", 20, self._top_right, tooltip="Настройки")
        self._settings_btn.clicked.connect(self._open_settings)
        self._close_btn = _icon_btn("ph.x-thin", 20, self._top_right, tooltip="Закрыть")
        self._close_btn.clicked.connect(self.close)

        # Center play/pause
        self._center_btn = QPushButton(self)
        self._center_btn.setFixedSize(60, 60)
        self._center_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._center_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._center_btn.setStyleSheet("background: transparent; border: none;")
        self._center_btn.setIconSize(QSize(40, 40))
        self._center_btn.clicked.connect(self._toggle_pause)
        self._update_center_icon()

        # Side navigation (visual only — clicks handled in mousePressEvent)
        self._left_nav = QLabel(self)
        self._left_nav.setPixmap(_icon("ph.caret-left-light", CLR_DIM).pixmap(QSize(20, 20)))
        self._left_nav.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._left_nav.setStyleSheet("background: transparent;")
        self._left_nav.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self._right_nav = QLabel(self)
        self._right_nav.setPixmap(_icon("ph.caret-right-light", CLR_DIM).pixmap(QSize(20, 20)))
        self._right_nav.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._right_nav.setStyleSheet("background: transparent;")
        self._right_nav.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        # Bottom: timer + counter
        self._timer_label = QLabel(self)
        self._timer_label.setStyleSheet(
            "color: rgba(255,255,255,115); font-size: 20px; background: transparent;")
        self._timer_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self._counter_label = QLabel(self)
        self._counter_label.setStyleSheet(
            "color: rgba(255,255,255,90); font-size: 20px; background: transparent;")
        self._counter_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        # Coffee icon (always visible when paused)
        self._coffee_label = QLabel(self)
        self._coffee_label.setPixmap(
            _icon("ph.coffee-light", CLR_NORMAL).pixmap(QSize(20, 20)))
        self._coffee_label.setFixedSize(20, 20)
        self._coffee_label.setStyleSheet("background: transparent;")
        self._coffee_label.hide()

        # Progress bar
        self._progress_bar = ProgressBar(self)

        # Collect hover-only widgets
        self._hover_widgets = [
            self._top_left, self._top_right, self._center_btn,
            self._left_nav, self._right_nav,
            self._timer_label, self._counter_label, self._progress_bar,
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

    # ------------------------------------------------------------------ Icons

    def _update_center_icon(self):
        if self._paused:
            self._center_btn.setIcon(_icon("ph.play-fill", CLR_HOVER, 40))
        else:
            self._center_btn.setIcon(_icon("ph.pause-fill", CLR_HOVER, 40))

    def _update_coffee(self):
        if self._paused:
            color = CLR_WARNING if self._is_warning else CLR_NORMAL
            self._coffee_label.setPixmap(
                _icon("ph.coffee-light", color).pixmap(QSize(20, 20)))
            self._coffee_label.setFixedSize(20, 20)
            self._coffee_label.show()
        else:
            self._coffee_label.hide()
        self._layout_bottom(self.width(), self.height())

    def _layout_bottom(self, w, h):
        lbl_h = 24
        bottom_y = h - lbl_h - 8
        x = 10
        if self._coffee_label.isVisible():
            self._coffee_label.setFixedSize(20, 20)
            self._coffee_label.move(x, bottom_y + 2)
            x += 26
        self._timer_label.setGeometry(x, bottom_y, 80, lbl_h)
        self._counter_label.setGeometry(w - 70, bottom_y, 60, lbl_h)
        self._counter_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

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
        self._total_time = seconds
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
        if self._play_order:
            img = self._images[self._play_order[self._current_idx]]
            warn_secs = auto_warn_seconds(img.timer)
        else:
            warn_secs = 0
        self._is_warning = self._countdown <= warn_secs and self._countdown > 0

        idx = self._hover_widgets.index(self._timer_label)
        # Only change color, not font-size (font-size managed by resizeEvent)
        if self._is_warning:
            self._timer_color = "rgba(255,85,85,200)"
            self._opacity_effects[idx].setOpacity(1.0)
        else:
            self._timer_color = "rgba(255,255,255,115)"
            if not self._controls_visible:
                self._opacity_effects[idx].setOpacity(0.0)
        self._timer_label.setStyleSheet(
            f"color: {self._timer_color}; font-size: 20px; background: transparent;")
        self._timer_label.setText(t)

        # Progress bar
        if self._total_time > 0:
            elapsed = self._total_time - self._countdown
            self._progress_bar.set_progress(elapsed / self._total_time, self._is_warning)

        self._update_coffee()

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

    def _show_help(self):
        if hasattr(self, "_help_overlay") and self._help_overlay.isVisible():
            self._help_overlay.hide()
            return
        self._help_overlay = QLabel(self)
        self._help_overlay.setStyleSheet(
            "background-color: rgba(0, 0, 0, 210); color: rgba(255,255,255,200); "
            "font-size: 20px; padding: 20px;")
        self._help_overlay.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._help_overlay.setText(
            "Пробел — пауза / продолжить\n"
            "\u2190  \u2192  — предыдущее / следующее\n"
            "F11 — полный экран\n"
            "Esc — выйти из полного экрана\n"
            "H — эта справка\n\n"
            "ПКМ + перетаскивание — переместить окно\n"
            "Края окна — изменить размер"
        )
        self._help_overlay.setGeometry(self.rect())
        self._help_overlay.show()
        self._help_overlay.mousePressEvent = lambda e: self._help_overlay.hide()

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()
        self._update_display()

    def _open_settings(self):
        if not self._paused:
            self._toggle_pause()
        if self.on_close:
            self.on_close(return_only=True)

    def _finish(self):
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
        if event.key() == Qt.Key.Key_F11:
            self._toggle_fullscreen()
        elif event.key() == Qt.Key.Key_Escape:
            if self.isFullScreen():
                self._toggle_fullscreen()
            elif hasattr(self, "_help_overlay") and self._help_overlay.isVisible():
                self._help_overlay.hide()
        elif event.key() == Qt.Key.Key_Space:
            self._toggle_pause()
        elif event.key() == Qt.Key.Key_Left:
            self._prev()
        elif event.key() == Qt.Key.Key_Right:
            self._next()
        elif event.key() == Qt.Key.Key_H:
            self._show_help()
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
        self._gradient.setGeometry(0, 0, w, h)

        # Fixed sizes
        btn_sz = 26
        margin = 8

        # Top left: info
        self._top_left.setGeometry(margin, margin, btn_sz, btn_sz)
        self._info_btn.setGeometry(0, 0, btn_sz, btn_sz)

        # Top right: settings + close
        gap = 4
        tr_w = btn_sz * 2 + gap
        self._top_right.setGeometry(w - tr_w - margin, margin, tr_w, btn_sz)
        self._settings_btn.setGeometry(0, 0, btn_sz, btn_sz)
        self._close_btn.setGeometry(btn_sz + gap, 0, btn_sz, btn_sz)

        # Center
        self._center_btn.move((w - 60) // 2, (h - 60) // 2)

        # Side nav
        nav_y = (h - 40) // 2
        self._left_nav.setGeometry(4, nav_y, 25, 40)
        self._right_nav.setGeometry(w - 29, nav_y, 25, 40)

        # Bottom layout
        self._layout_bottom(w, h)

        # Progress bar at very bottom
        self._progress_bar.setGeometry(0, h - 3, w, 3)

        self._update_display()

    def paintEvent(self, event):
        super().paintEvent(event)

    def enterEvent(self, event):
        super().enterEvent(event)
        self._gradient.show()
        self._gradient.raise_()
        # Raise all controls above gradient
        for w in self._hover_widgets:
            w.raise_()
        self._coffee_label.raise_()
        self._fade_controls(True)

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self._gradient.hide()
        self._fade_controls(False)

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
            elif pos.x() < NAV_ZONE and self._controls_visible:
                self._prev()
                event.accept()
            elif pos.x() > self.width() - NAV_ZONE and self._controls_visible:
                self._next()
                event.accept()
            else:
                event.ignore()

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()
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
