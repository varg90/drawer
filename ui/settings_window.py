"""SettingsWindow — main app window, composes TimerPanel + BottomBar."""
import os
import random
import weakref
import qtawesome as qta
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                              QFileDialog, QScrollArea, QLabel)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import (QColor, QLinearGradient, QPainter, QPainterPath,
                         QDragEnterEvent, QDropEvent, QIcon)
from PyQt6.QtCore import QRectF
from core.constants import SUPPORTED_FORMATS
from core.class_mode import groups_to_timers
from core.file_utils import filter_image_files, scan_folder
from core.session import save_session, load_session
from core.models import ImageItem
from ui.theme import Theme
from ui.scales import S, base_value
from ui.icons import Icons
from ui.widgets import (make_icon_btn, make_icon_toggle,
                         make_centered_header)
from ui.snap import SnapMixin
from ui.rounded_window import RoundedWindowMixin
from ui.timer_panel import TimerPanel
from ui.bottom_bar import BottomBar
from ui.platform import setup_frameless_native


class _InsetPanel(QWidget):
    """Panel with rounded background."""

    def __init__(self, bg_color="#120e0a", radius=6, parent=None):
        super().__init__(parent)
        self._bg = QColor(bg_color)
        self._radius = radius

    def set_bg(self, color_hex):
        self._bg = QColor(color_hex)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), self._radius, self._radius)
        p.fillPath(path, self._bg)
        p.end()


class SettingsWindow(QMainWindow, SnapMixin, RoundedWindowMixin):
    images_changed = pyqtSignal()

    def __init__(self):
        QMainWindow.__init__(self)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setWindowTitle("Drawer")
        self.setWindowIcon(QIcon(os.path.join(os.path.dirname(__file__), "..", "drawer.ico")))
        self.setMinimumSize(base_value("MAIN_MIN"), base_value("MAIN_MIN"))
        self.resize(S.MAIN_W, S.MAIN_H)
        self._resize_edge = None
        self._resize_start = None
        self._resize_geo = None
        self._resize_outline = None
        self._last_edge = None
        self.setMouseTracking(True)

        self.images = []
        self.viewer = None
        self.editor = None
        self.theme = Theme("dark")

        self._topmost = False
        self._shuffle = True

        self._build_ui()
        self._apply_theme()
        SnapMixin.__init__(self)
        self.rounded_init()
        self._restore_session()
        self.setAcceptDrops(True)

    @property
    def _editor_visible(self):
        return self.editor is not None and self.editor.isVisible()

    # ------------------------------------------------------------------ UI

    def _build_ui(self):
        central = QWidget()
        central.setMouseTracking(True)
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(S.MARGIN, S.MARGIN_TOP, S.MARGIN, S.MARGIN_BOTTOM)
        root.setSpacing(0)

        # ── 1. Header ──────────────────────────────────────────────────────
        self._help_btn = make_icon_btn(Icons.INFO, self.theme.text_hint,
                                       size=S.ICON_HEADER, tooltip="Help")
        self._help_btn.clicked.connect(self._show_help)

        self._topmost_btn = make_icon_toggle(
            Icons.TOPMOST_ON, Icons.TOPMOST_OFF, self._topmost, self.theme,
            size=S.ICON_HEADER)
        self._topmost_btn.setToolTip("Always on top")
        self._topmost_btn.clicked.connect(self._toggle_topmost)

        self._accent_btn = make_icon_btn(Icons.PALETTE, self.theme.accent,
                                          size=S.ICON_HEADER, tooltip="Accent color")
        self._accent_btn.clicked.connect(self._pick_accent)

        self._theme_btn = make_icon_btn(
            Icons.THEME_DARK if self.theme.name == "dark" else Icons.THEME_LIGHT,
            self.theme.text_hint, size=S.ICON_HEADER)
        self._theme_btn.clicked.connect(self._toggle_theme)

        self._min_btn = make_icon_btn(Icons.MINIMIZE, self.theme.text_hint,
                                      size=S.ICON_HEADER, tooltip="Minimize")
        self._min_btn.clicked.connect(self.showMinimized)

        self._close_btn = make_icon_btn(Icons.CLOSE, self.theme.text_hint,
                                        size=S.ICON_HEADER, tooltip="Close")
        self._close_btn.clicked.connect(self.close)

        header_layout, self._title = make_centered_header(
            "Drawer",
            [self._help_btn, self._accent_btn, self._theme_btn],
            [self._topmost_btn, self._min_btn, self._close_btn],
            self.theme,
        )
        root.addLayout(header_layout)

        # ── 2. Inset panel wraps the timer section ─────────────────────────
        self._panel = _InsetPanel(self.theme.bg_panel, S.PANEL_RADIUS)
        panel_lay = QVBoxLayout(self._panel)
        panel_lay.setContentsMargins(S.PANEL_PADDING, S.PANEL_PADDING,
                                      S.PANEL_PADDING, S.PANEL_PADDING)
        panel_lay.setSpacing(0)

        self._timer_panel = TimerPanel(self.theme, parent=self._panel)
        self._timer_panel.timer_config_changed.connect(self._on_timer_config_changed)
        panel_lay.addWidget(self._timer_panel)

        # Panel centered between header and bottom bar
        root.addStretch()
        root.addWidget(self._panel)
        root.addStretch()

        # ── 4. BottomBar ──────────────────────────────────────────────────
        self._bottom_bar = BottomBar(self.theme, parent=self)
        self._bottom_bar.start_clicked.connect(self._start_slideshow)
        self._bottom_bar.add_clicked.connect(self._open_editor)
        root.addWidget(self._bottom_bar)

        # ── Initialize display ─────────────────────────────────────────────
        self._update_summary()

    # ------------------------------------------------------------------ Proxy for editor_panel compatibility

    def get_timer_seconds(self):
        return self._timer_panel.get_timer_seconds()

    # ------------------------------------------------------------------ Signal handlers

    def _on_timer_config_changed(self):
        """TimerPanel changed mode, preset, or tiers — update images and summary."""
        mode = self._timer_panel.timer_mode
        if mode == "quick":
            timer = self._timer_panel.get_timer_seconds()
            for img in self.images:
                img.timer = timer
        else:
            if self.images:
                self._timer_panel.auto_distribute(len(self.images))
                self._apply_class_timers()
        self._update_summary()
        if self._editor_visible:
            self.editor.refresh(self.images)
            self._sync_editor_tiers()

    def _sync_editor_tiers(self):
        """Push configured tier timer values to editor panel."""
        if not self._editor_visible:
            return
        groups = self._timer_panel.class_groups
        if groups:
            self.editor._panel._all_tier_timers = [t for _, t in groups]
        else:
            self.editor._panel._all_tier_timers = []

    def _apply_class_timers(self):
        groups = self._timer_panel.class_groups
        if groups:
            timers = groups_to_timers(groups)
            for i, img in enumerate(self.images):
                if getattr(img, "pinned", False):
                    continue
                img.timer = timers[i] if i < len(timers) else timers[-1]

    def _update_summary(self):
        n = len(self.images)
        mode = self._timer_panel.timer_mode
        if mode == "quick":
            self._bottom_bar.update_summary_quick(n, self._timer_panel.get_timer_seconds())
        else:
            self._bottom_bar.update_summary_class(n, self._timer_panel.class_groups)

    # ------------------------------------------------------------------ Theme

    def _apply_theme(self):
        t = self.theme
        self.setStyleSheet(
            f"background-color: transparent; color: {t.text_primary}; "
            f"font-family: 'Lexend';"
        )
        self._panel.set_bg(t.bg_panel)

        self._title.recolor(t.text_header)

        # Header icons
        self._help_btn.setIcon(qta.icon(Icons.INFO, color=t.text_hint))
        _topmost_icon = Icons.TOPMOST_ON if self._topmost else Icons.TOPMOST_OFF
        _topmost_color = t.text_secondary if self._topmost else t.text_hint
        self._topmost_btn.setIcon(qta.icon(_topmost_icon, color=_topmost_color))
        _theme_icon = Icons.THEME_DARK if t.name == "dark" else Icons.THEME_LIGHT
        self._theme_btn.setIcon(qta.icon(_theme_icon, color=t.text_hint))
        self._min_btn.setIcon(qta.icon(Icons.MINIMIZE, color=t.text_hint))
        self._close_btn.setIcon(qta.icon(Icons.CLOSE, color=t.text_hint))
        self._accent_btn.setIcon(qta.icon(Icons.PALETTE, color=t.accent))

        # Composed widgets
        self._timer_panel.theme = t
        self._timer_panel.apply_theme()
        self._bottom_bar.theme = t
        self._bottom_bar.apply_theme()

        self._dismiss_help()
        self.update()

    # ------------------------------------------------------------------ Rounded painting

    def corner_radii(self):
        r = S.WINDOW_RADIUS
        # When editor is snapped to our right, round left corners only
        if self._snapped_children:
            return (r, 0, 0, r)
        return (r, r, r, r)

    def _bg_color(self):
        return QColor(self.theme.bg)

    def _border_color(self):
        return QColor(self.theme.border)

    def _bg_brush(self):
        return QColor(self.theme.bg)

    def paintEvent(self, event):
        self._paint_rounded(event)

    # ------------------------------------------------------------------ Window dragging

    def _edge_at(self, pos, cursor_only=False):
        """Detect if cursor is near any edge. For square resize, returns the
        quadrant corner (tl/tr/bl/br) so the anchor is always the opposite corner."""
        r = self.rect()
        e = S.RESIZE_CURSOR_W if cursor_only else S.RESIZE_GRIP_W
        near_top = pos.y() < e
        near_bottom = pos.y() > r.height() - e
        near_left = pos.x() < e
        near_right = pos.x() > r.width() - e
        if not (near_top or near_bottom or near_left or near_right):
            return None
        # Map to quadrant corner for square resize
        in_top_half = pos.y() < r.height() / 2
        in_left_half = pos.x() < r.width() / 2
        if in_top_half and in_left_half:
            return "tl"
        if in_top_half and not in_left_half:
            return "tr"
        if not in_top_half and in_left_half:
            return "bl"
        return "br"

    def _cursor_for_edge(self, edge):
        if edge in ("tl", "br"):
            return Qt.CursorShape.SizeFDiagCursor
        if edge in ("tr", "bl"):
            return Qt.CursorShape.SizeBDiagCursor
        return Qt.CursorShape.ArrowCursor

    def _calc_resize_geo(self, delta):
        """Calculate target square geometry from drag delta.
        _edge_at always returns a corner (tl/tr/bl/br), so both axes are present."""
        from PyQt6.QtCore import QRect
        geo = self._resize_geo
        e = self._resize_edge
        dx = delta.x() if "r" in e else -delta.x()
        dy = delta.y() if "b" in e else -delta.y()
        d = max(dx, dy)
        screen = self.screen()
        max_size = screen.availableGeometry().height() if screen else 900
        new_size = max(base_value("MAIN_MIN"), min(max_size, geo.width() + d))
        new_geo = QRect(geo)
        if "l" in e:
            new_geo.setLeft(geo.right() - new_size + 1)
        else:
            new_geo.setRight(geo.left() + new_size - 1)
        if "t" in e:
            new_geo.setTop(geo.bottom() - new_size + 1)
        else:
            new_geo.setBottom(geo.top() + new_size - 1)
        return new_geo

    def _show_resize_outline(self):
        """Create a semi-transparent overlay showing the target resize rectangle."""
        self._resize_outline = QWidget()
        self._resize_outline.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool)
        t = self.theme
        self._resize_outline.setStyleSheet(
            f"background-color: {t.bg};"
            f"border: 2px solid {t.accent};"
            f"border-radius: {S.WINDOW_RADIUS}px;")
        self._resize_outline.setWindowOpacity(0.5)
        self._resize_outline.setGeometry(self.geometry())
        self._resize_outline.show()

    def _hide_resize_outline(self):
        if self._resize_outline is not None:
            self._resize_outline.close()
            self._resize_outline.deleteLater()
            self._resize_outline = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            edge = self._edge_at(event.pos(), cursor_only=True)
            if edge:
                self._resize_edge = edge
                self._resize_start = event.globalPosition().toPoint()
                self._resize_geo = self.geometry()
                self._show_resize_outline()
                event.accept()
                return
        self._resize_edge = None
        self.snap_mouse_press(event)

    def mouseMoveEvent(self, event):
        if not event.buttons():
            edge = self._edge_at(event.pos(), cursor_only=True)
            if edge != self._last_edge:
                self._last_edge = edge
                self.setCursor(self._cursor_for_edge(edge) if edge else Qt.CursorShape.ArrowCursor)
            return
        if self._resize_edge:
            delta = event.globalPosition().toPoint() - self._resize_start
            new_geo = self._calc_resize_geo(delta)
            if self._resize_outline:
                self._resize_outline.setGeometry(new_geo)
            event.accept()
            return
        self.snap_mouse_move(event)

    def mouseReleaseEvent(self, event):
        if self._resize_edge:
            if self._resize_outline:
                target = self._resize_outline.geometry()
                self._hide_resize_outline()
                self.setGeometry(target)
            self._resize_edge = None
            self._apply_user_scale()
            return
        self.snap_mouse_release(event)

    # ------------------------------------------------------------------ Resize scale

    def _apply_user_scale(self):
        """Recalculate UI scale from current window size and rebuild everything."""
        from ui.scales import rescale_user, base_value
        base_size = base_value("MAIN_W")
        user_factor = self.width() / base_size
        rescale_user(user_factor)

        # Save widget state before full rebuild
        timer_state = self._timer_panel.save_state()
        bottom_state = self._bottom_bar.save_state()

        # Rebuild entire UI from scratch with new S.* values
        self._dismiss_help()
        self._build_ui()
        self._timer_panel.restore_state({**timer_state, **bottom_state})
        self._bottom_bar.restore_state({**timer_state, **bottom_state})
        self._apply_theme()

        # Rebuild editor if open
        if self._editor_visible:
            self.editor.resize(S.EDITOR_W, self.height())
            self.editor._build_ui()
            self.editor._apply_theme()
            # Reposition snapped editor
            if self.editor._snapped_to is not None:
                snap_pos = self.editor._calc_snap_pos(self, "right")
                if snap_pos:
                    self.editor.move(snap_pos)
            self.editor.update()

        self.update()

    # ------------------------------------------------------------------ Help / Theme / Accent

    def _dismiss_help(self):
        if hasattr(self, "_help_overlay") and self._help_overlay is not None:
            self._help_overlay.deleteLater()
            self._help_overlay = None

    def _show_help(self):
        if hasattr(self, "_help_overlay") and self._help_overlay is not None:
            self._dismiss_help()
            return
        t = self.theme
        cw = self.centralWidget()
        overlay = QWidget(cw)
        overlay.setGeometry(cw.rect())
        overlay.setStyleSheet(
            f"background-color: rgba({t.bg_rgb}, 230);"
            f"border-radius: {S.WINDOW_RADIUS}px;")

        layout = QVBoxLayout(overlay)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet(
            f"QScrollArea {{ background: transparent; }}"
            f"QScrollBar:vertical {{ width: 4px; background: transparent; }}"
            f"QScrollBar::handle:vertical {{ background: {t.text_hint}; }}"
            f"QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}")
        scroll.mousePressEvent = lambda e: self._dismiss_help()

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        content.mousePressEvent = lambda e: self._dismiss_help()
        inner = QVBoxLayout(content)
        inner.setContentsMargins(16, 14, 16, 12)

        info_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "info_main.txt")
        try:
            with open(info_path, encoding="utf-8") as f:
                info_text = f.read().replace("\n", "<br>")
        except FileNotFoundError:
            info_text = "Drawer 0.3.1"
        lbl = QLabel(info_text)
        lbl.setStyleSheet(f"color: {t.text_primary}; font-size: 11px;")
        lbl.setWordWrap(True)
        lbl.mousePressEvent = lambda e: self._dismiss_help()
        inner.addWidget(lbl)
        inner.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll)

        overlay.raise_()
        overlay.show()
        self._help_overlay = overlay

    def _toggle_theme(self):
        self.theme.toggle()
        self._apply_theme()
        self._refresh_editor_theme()

    def _pick_accent(self):
        from ui.accent_picker import AccentPicker
        if hasattr(self, '_accent_picker') and self._accent_picker is not None:
            self._accent_picker.close()
            self._accent_picker = None
            return
        picker = AccentPicker(self.theme.accent, self.theme, parent=self)
        picker.color_changed.connect(self._on_accent_changed)
        picker.destroyed.connect(lambda: setattr(self, '_accent_picker', None))
        picker.show_near(self._accent_btn)
        self._accent_picker = picker

    def _on_accent_changed(self, color):
        self.theme.accent = color
        self._apply_theme()
        self._refresh_editor_theme()

    def _refresh_editor_theme(self):
        if self._editor_visible:
            self.editor.theme = self.theme
            self.editor._apply_theme()
            self.editor._panel.theme = self.theme
            self.editor._panel._apply_theme()
            self.editor._panel._restyle_groups()

    # ------------------------------------------------------------------ Toggle methods

    def _toggle_topmost(self):
        self._topmost = not self._topmost
        t = self.theme
        _icon = Icons.TOPMOST_ON if self._topmost else Icons.TOPMOST_OFF
        _color = t.text_secondary if self._topmost else t.text_hint
        self._topmost_btn.setIcon(qta.icon(_icon, color=_color))

    # ------------------------------------------------------------------ Image management

    def _add_files(self):
        exts = " ".join(f"*{e}" for e in SUPPORTED_FORMATS)
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select files", "",
            f"Images ({exts});;All files (*)"
        )
        if paths:
            timer = self._timer_panel.get_timer_seconds()
            for p in filter_image_files(paths):
                self.images.append(ImageItem(path=p, timer=timer))
            self._on_images_changed()

    def _add_folder(self, folder):
        timer = self._timer_panel.get_timer_seconds()
        for p in scan_folder(folder):
            self.images.append(ImageItem(path=p, timer=timer))
        self._on_images_changed()

    def _on_images_changed(self):
        self._update_summary()
        self.images_changed.emit()
        if self._editor_visible:
            self.editor.refresh(self.images)

    def _open_editor(self):
        if self._editor_visible:
            self.editor.close()
            return
        from ui.image_editor_window import ImageEditorWindow
        view = getattr(self, "_last_editor_view", "list")
        self.editor = ImageEditorWindow(
            self.images, self.theme, parent=self, view_mode=view, shuffle=self._shuffle)
        self.editor.images_updated.connect(self._on_editor_update)
        self.editor.shuffle_changed.connect(self._on_shuffle_changed)
        pos = self.geometry()
        self.editor.move(pos.right(), pos.top())
        self.editor.resize(S.EDITOR_W, S.MAIN_H)
        self.editor.show()
        self.editor._snapped_to = (weakref.ref(self), "right")
        self._snapped_children.append((weakref.ref(self.editor), "right"))
        self._sync_editor_tiers()
        self.update()  # repaint with snapped corner radii
        self.editor.update()

    def _on_editor_close(self):
        if self.editor is not None:
            self._last_editor_view = self.editor._view_mode
        self.editor = None
        self.update()  # repaint with all corners rounded

    def _on_shuffle_changed(self, value):
        self._shuffle = value

    def _on_editor_update(self, images):
        self.images = list(images)
        self._update_summary()

    # ------------------------------------------------------------------ Drag and drop

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        paths = [u.toLocalFile() for u in urls]
        timer = self._timer_panel.get_timer_seconds()
        added = 0
        for p in paths:
            if os.path.isdir(p):
                for fp in scan_folder(p):
                    self.images.append(ImageItem(path=fp, timer=timer))
                    added += 1
            elif os.path.isfile(p) and os.path.splitext(p)[1].lower() in SUPPORTED_FORMATS:
                self.images.append(ImageItem(path=p, timer=timer))
                added += 1
        if added:
            self._on_images_changed()
        event.acceptProposedAction()

    # ------------------------------------------------------------------ Slideshow

    def _start_slideshow(self):
        if not self.images:
            return

        mode = self._timer_panel.timer_mode
        # Assign timers before shuffling so tiers stay correct
        if mode == "quick":
            timer = self._timer_panel.get_timer_seconds()
            for img in self.images:
                if not img.pinned:
                    img.timer = timer
        elif self._timer_panel.class_groups:
            timers = groups_to_timers(self._timer_panel.class_groups)
            idx = 0
            for img in self.images:
                if not img.pinned and idx < len(timers):
                    img.timer = timers[idx]
                    idx += 1

        if self._shuffle:
            pinned = [img for img in self.images if img.pinned]
            unpinned = [img for img in self.images if not img.pinned]
            random.shuffle(unpinned)
            show_images = unpinned + pinned
        else:
            show_images = list(self.images)

        if mode == "class" and self._timer_panel.class_groups:
            show_images.sort(key=lambda img: img.timer)

        settings = {
            "order": "sequential",
            "topmost": self._topmost,
            "viewer_size": getattr(self, "_last_viewer_size", None),
            "session_limit": self._bottom_bar.get_session_limit(),
            "focus_enabled": self._bottom_bar.focus_enabled,
            "focus_app": self._bottom_bar.focus_app,
        }
        from ui.viewer_window import ViewerWindow
        self.viewer = ViewerWindow(show_images, settings,
                                   on_close=self._on_viewer_closed,
                                   settings_window=self)
        self.viewer.show()
        if self._editor_visible:
            self.editor.hide()
        self.hide()

    def _on_viewer_closed(self, return_only=False):
        if self.viewer and not self.viewer.isFullScreen():
            self._last_viewer_size = [self.viewer.width(), self.viewer.height()]
        if return_only:
            self.show()
        else:
            self.viewer = None
            self.show()
        if self.editor is not None and not self._editor_visible:
            self.editor.show()

    # ------------------------------------------------------------------ Session save/restore

    def _restore_session(self):
        data = load_session()
        if not data:
            return
        images_data = data.get("images", [])
        self.images = [ImageItem.from_dict(d) for d in images_data]
        self.images = [img for img in self.images if os.path.isfile(img.path)]

        self._topmost = data.get("topmost", False)
        self._shuffle = data.get("shuffle", True)
        self._last_editor_view = data.get("editor_view", "list")
        self._last_viewer_size = data.get("viewer_size")

        # Restore composed widgets
        self._timer_panel.restore_state(data)
        self._bottom_bar.restore_state(data)

        saved_size = data.get("window_size")
        if saved_size:
            screen = self.screen()
            max_h = screen.availableGeometry().height() if screen else 900
            saved_size = max(base_value("MAIN_MIN"), min(saved_size, max_h))
            self.resize(saved_size, saved_size)

        theme_name = data.get("theme", "dark")
        accent = data.get("accent")
        if accent:
            self.theme.accent = accent
        if theme_name != self.theme.name:
            self.theme.toggle()

        self._apply_theme()

        # Rebuild class-mode groups so images get proper timers
        if self._timer_panel.timer_mode == "class" and self.images:
            self._timer_panel.auto_distribute(len(self.images))
            self._apply_class_timers()

        self._update_summary()

    def _save_session(self):
        # Collect state from composed widgets
        timer_state = self._timer_panel.save_state()
        bottom_state = self._bottom_bar.save_state()

        data = {
            "images": [img.to_dict() for img in self.images],
            **timer_state,
            **bottom_state,
            "topmost": self._topmost,
            "shuffle": self._shuffle,
            "theme": self.theme.name,
            "accent": self.theme.accent,
            "editor_view": (
                self.editor._view_mode if self._editor_visible
                else getattr(self, "_last_editor_view", "list")
            ),
            "viewer_size": getattr(self, "_last_viewer_size", None),
            "editor_pos": [self.editor.x(), self.editor.y()] if self.editor and self.editor.isVisible() else None,
            "editor_size": [self.editor.width(), self.editor.height()] if self.editor and self.editor.isVisible() else None,
            "window_size": self.width(),
        }
        save_session(data)

    # ------------------------------------------------------------------ Close

    def closeEvent(self, event):
        if self.viewer is not None:
            event.ignore()
            if self._editor_visible:
                self.editor.hide()
            self.hide()
            self.viewer.show()
        else:
            self._save_session()
            if self.editor is not None:
                self.editor.close()
            self.snap_cleanup()
            event.accept()
