# ui/editor_panel.py
"""EditorPanel — reusable image editor panel widget for Drawer.

Can be embedded inside a settings window (docked) or shown standalone (detached).
"""

import os
from collections import OrderedDict

import qtawesome as qta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QFileDialog, QSlider,
    QScrollArea, QStackedWidget, QMessageBox, QSizePolicy,
)
from PyQt6.QtGui import QPixmap, QIcon, QColor, QBrush, QImage, QPainter, QPainterPath, QPalette
from PyQt6.QtCore import Qt, QRectF, pyqtSignal, QSize, QTimer, QThread

from core.constants import SUPPORTED_FORMATS
from core.file_utils import filter_image_files, scan_folder
from core.models import ImageItem
from core.timer_logic import format_time
from ui.theme import _mix, _darken
from core.cloud.cache import CacheManager
from ui.scales import S
from ui.icons import Icons
from ui.widgets import make_icon_btn


class _ColorLine(QWidget):
    """1px line that paints its own color, immune to stylesheet inheritance."""
    def __init__(self, color, parent=None):
        super().__init__(parent)
        self._color = color
        self.setFixedHeight(S.COLOR_LINE_H)
    def set_color(self, color):
        self._color = color
        self.update()
    def paintEvent(self, event):
        QPainter(self).fillRect(self.rect(), self._color)


def _short_label(secs):
    """Convert seconds to compact label: 30→'30s', 60→'1m', 3600→'1h'."""
    if secs >= 3600 and secs % 3600 == 0:
        return f"{secs // 3600}h"
    if secs >= 60 and secs % 60 == 0:
        return f"{secs // 60}m"
    return f"{secs}s"


def _sort_group_items(items):
    """Sort items so pinned come first, preserving relative order within each group."""
    pinned = [i for i in items if getattr(i[1], "pinned", False)]
    unpinned = [i for i in items if not getattr(i[1], "pinned", False)]
    return pinned + unpinned


# ---------------------------------------------------------------------------
# Background image loader (reused from image_editor_window.py)
# ---------------------------------------------------------------------------

class PixmapLoader(QThread):
    """Load images from disk in a background thread."""
    loaded = pyqtSignal(str, QImage)

    def __init__(self, paths, max_size=None):
        super().__init__()
        self._paths = paths
        self._max = max_size if max_size is not None else S.GRID_MAX
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        for path in self._paths:
            if self._cancel:
                return
            img = QImage(path)
            if not img.isNull():
                img = img.scaled(
                    self._max, self._max,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.loaded.emit(path, img)


# ---------------------------------------------------------------------------
# Clickable tile label for grid view
# ---------------------------------------------------------------------------

class ClickableLabel(QLabel):
    """QLabel with click-to-select support for grid tiles."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected = False

    def mousePressEvent(self, event):
        # Walk up the parent chain to find EditorPanel (self.window() returns
        # the top-level window, which may be SettingsWindow, not EditorPanel).
        editor = self.parent()
        while editor is not None:
            if hasattr(editor, "_on_tile_click"):
                break
            editor = editor.parent()
        if editor is None:
            return

        if event.button() == Qt.MouseButton.RightButton:
            editor._show_tile_context_menu(self, event.globalPosition().toPoint())
            return

        mods = event.modifiers()
        ctrl = bool(mods & Qt.KeyboardModifier.ControlModifier)
        shift = bool(mods & Qt.KeyboardModifier.ShiftModifier)
        editor._on_tile_click(self, ctrl, shift)


# ---------------------------------------------------------------------------
# Flow layout helper (reused from image_editor_window.py)
# ---------------------------------------------------------------------------

def _flow_position(labels, container_width, sz, gap=1):
    """Position labels in a flow layout. Returns total height."""
    x, y, row_h = 0, 0, 0
    for lbl in labels:
        pix = lbl.pixmap()
        if pix and not pix.isNull():
            w, h = pix.width(), pix.height()
        else:
            w, h = sz, sz
        if x + w > container_width and x > 0:
            x = 0
            y += row_h + gap
            row_h = 0
        lbl.setFixedSize(w, h)
        lbl.move(x, y)
        x += w + gap
        row_h = max(row_h, h)
    return y + row_h if labels else 0


# ---------------------------------------------------------------------------
# EditorPanel
# ---------------------------------------------------------------------------

class EditorPanel(QWidget):
    """Reusable image editor panel: toolbar, grouped file list, grid view."""

    images_updated = pyqtSignal(list)
    close_requested = pyqtSignal()
    shuffle_changed = pyqtSignal(bool)

    def __init__(self, images, theme, parent=None, view_mode="list", shuffle=True):
        super().__init__(parent)
        self.images = list(images)
        self.theme = theme
        self._parent = parent
        self._view_mode = view_mode if view_mode in ("list", "grid") else "list"
        self._shuffle = shuffle

        self._pix_cache = {}          # path -> QPixmap
        self._loader = None           # PixmapLoader thread
        self._selected_tiles = set()  # set of ClickableLabel
        self._last_clicked_tile = None

        self._list_groups = []   # list of (header_btn, list_widget)
        self._grid_groups = []   # list of (header_btn, grid_widget)
        self._all_tier_timers = []  # all configured tier timer values

        # Per-group collapsed state, keyed by timer_val (0 = reserve).
        # Preserved across rebuilds so toggling tiers doesn't force-expand groups.
        self._collapsed_tiers = {0}

        self._needs_initial_rebuild = True

        self._build_ui()
        self._apply_theme()
        self._set_view_mode(self._view_mode)

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # --- Stacked widget: list / grid ---
        self._stack = QStackedWidget()

        # List scroll
        self._list_scroll = QScrollArea()
        self._list_scroll.setWidgetResizable(True)
        self._list_scroll.installEventFilter(self)
        self._list_scroll.viewport().installEventFilter(self)
        self._list_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._list_scroll.setAcceptDrops(True)
        self._list_scroll.dragEnterEvent = self._drag_enter
        self._list_scroll.dropEvent = self._drop_event

        self._list_container = QWidget()
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(S.LIST_SPACING)
        self._list_layout.addStretch()
        self._list_scroll.setWidget(self._list_container)
        self._stack.addWidget(self._list_scroll)

        # Grid scroll
        self._grid_scroll = QScrollArea()
        self._grid_scroll.setWidgetResizable(True)
        self._grid_scroll.installEventFilter(self)
        self._grid_scroll.viewport().installEventFilter(self)
        self._grid_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._grid_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._grid_scroll.setAcceptDrops(True)
        self._grid_scroll.dragEnterEvent = self._drag_enter
        self._grid_scroll.dropEvent = self._drop_event

        self._grid_container = QWidget()
        self._grid_layout = QVBoxLayout(self._grid_container)
        self._grid_layout.setContentsMargins(0, 0, 0, 0)
        self._grid_layout.setSpacing(S.GRID_SPACING)
        self._grid_layout.addStretch()
        self._grid_scroll.setWidget(self._grid_container)
        self._stack.addWidget(self._grid_scroll)

        root.addWidget(self._stack, 1)

        # --- Bottom controls ---
        bottom = QHBoxLayout()
        bottom.setSpacing(4)
        bottom.setContentsMargins(0, 0, 0, 0)

        # List/grid toggle
        bs = S.EDITOR_BTN_BOTTOM
        self._list_btn = make_icon_btn(
            Icons.LIST, self.theme.text_secondary,
            size=bs, tooltip="List view",
        )
        self._list_btn.clicked.connect(lambda: self._set_view_mode("list"))

        self._grid_btn = make_icon_btn(
            Icons.GRID, self.theme.text_secondary,
            size=bs, tooltip="Grid view",
        )
        self._grid_btn.clicked.connect(lambda: self._set_view_mode("grid"))

        # Zoom slider — hidden, used as internal state holder
        self._zoom_label = QLabel("Zoom:")
        self._zoom_label.hide()

        self._zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self._zoom_slider.setRange(S.GRID_MIN, S.GRID_MAX)
        self._zoom_slider.setValue(S.GRID_DEFAULT)
        self._zoom_slider.setFixedWidth(S.ZOOM_SLIDER_W)
        self._zoom_slider.valueChanged.connect(self._on_zoom)
        self._zoom_slider.hide()

        # Zoom icon buttons (grid mode only)
        self._zoom_out_btn = make_icon_btn(
            Icons.ZOOM_OUT, self.theme.text_hint,
            size=bs, tooltip="Zoom out",
        )
        self._zoom_in_btn = make_icon_btn(
            Icons.ZOOM_IN, self.theme.text_hint,
            size=bs, tooltip="Zoom in",
        )

        self._zoom_out_btn.clicked.connect(
            lambda: self._zoom_slider.setValue(
                max(self._zoom_slider.value() - S.GRID_ZOOM_STEP, self._zoom_slider.minimum())
            )
        )
        self._zoom_in_btn.clicked.connect(
            lambda: self._zoom_slider.setValue(
                min(self._zoom_slider.value() + S.GRID_ZOOM_STEP, self._zoom_slider.maximum())
            )
        )

        # Shuffle
        self._shuffle_btn = make_icon_btn(
            Icons.SHUFFLE, self.theme.accent if self._shuffle else self.theme.text_hint,
            size=bs, tooltip="Shuffle on start",
        )
        self._shuffle_btn.clicked.connect(self._toggle_shuffle)

        # Cache trash + size
        self._cache_btn = make_icon_btn(
            Icons.TRASH, self.theme.text_hint,
            size=bs, tooltip="Clear cache",
        )
        self._cache_btn.clicked.connect(self._clear_cache)
        self._cache_size_label = QLabel("")

        # Clear all
        self._clear_btn = make_icon_btn(
            Icons.ERASER, self.theme.text_hint,
            size=bs, tooltip="Clear all",
        )
        self._clear_btn.clicked.connect(self._clear)

        # Layout order: [List][Grid] | [ZoomOut][ZoomIn] | [Shuffle] <stretch> [Cache][CacheSize] | [Clear]
        bottom.addWidget(self._list_btn)
        bottom.addWidget(self._grid_btn)
        bottom.addSpacing(4)
        bottom.addWidget(self._zoom_out_btn)
        bottom.addWidget(self._zoom_in_btn)
        bottom.addSpacing(4)
        bottom.addWidget(self._shuffle_btn)
        bottom.addStretch()
        bottom.addWidget(self._cache_btn)
        bottom.addWidget(self._cache_size_label)
        bottom.addSpacing(2)
        bottom.addWidget(self._clear_btn)

        root.addSpacing(5)
        root.addSpacing(5)
        root.addLayout(bottom)

        self._update_bottom_controls()

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------

    def _apply_theme(self):
        t = self.theme
        self.setStyleSheet(f"background-color: transparent; color: {t.text_primary};")


        # Scroll area backgrounds + dashed drop-target border
        # Use #id selector to avoid bleeding into child widgets
        self._list_scroll.setObjectName("editorListScroll")
        self._grid_scroll.setObjectName("editorGridScroll")
        self._list_container.setObjectName("editorListContainer")
        self._grid_container.setObjectName("editorGridContainer")
        scrollbar_s = (
            f"QScrollBar:vertical {{ background: transparent; width: {S.SCROLLBAR_W}px; margin: 0; }}"
            f"QScrollBar::handle:vertical {{ background: {t.text_hint}; "
            f"min-height: {S.SCROLLBAR_HANDLE_MIN_H}px; border-radius: {S.SCROLLBAR_RADIUS}px; }}"
            f"QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}"
            f"QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}"
        )
        scroll_s = (
            f"QScrollArea#editorListScroll, QScrollArea#editorGridScroll {{ "
            f"background-color: transparent; border: none; }}"
            f" {scrollbar_s}"
        )
        container_s = (
            f"QWidget#editorListContainer, QWidget#editorGridContainer {{ "
            f"background-color: transparent; }}"
        )
        self._list_scroll.setStyleSheet(scroll_s)
        self._grid_scroll.setStyleSheet(scroll_s)
        self._list_container.setStyleSheet(container_s)
        self._grid_container.setStyleSheet(container_s)

        # Styles stored for reuse in rebuild
        self._list_style = (
            f"QListWidget {{ background-color: transparent; border: none; "
            f"font-family: 'Lexend'; font-size: {S.FONT_BUTTON}px; color: {t.text_primary}; }}"
            f"QListWidget::item {{ padding: {S.LIST_ITEM_PADDING}px; }}"
            f"QListWidget::item:selected {{ background-color: {t.bg_active}; }}"
        )
        # Mockup: plain text, accent-tinted, no bg/border
        _accent_header = _mix(t.accent, t.text_primary, 0.4) if t.name == "dark" else _darken(t.accent, 0.1)
        self._header_style = (
            f"background-color: transparent; color: {_accent_header}; "
            f"border: none; font-family: 'Lexend'; font-size: {S.FONT_LABEL}px; "
            f"font-weight: 500; padding: {S.HEADER_PADDING_TOP}px {S.HEADER_PADDING_H}px {S.HEADER_PADDING_BOTTOM}px; text-align: left;"
        )
        self._header_reserve_style = (
            f"background-color: transparent; color: {t.text_hint}; "
            f"border: none; font-family: 'Lexend'; font-size: {S.FONT_LABEL}px; "
            f"font-weight: 500; padding: {S.HEADER_PADDING_TOP}px {S.HEADER_PADDING_H}px {S.HEADER_PADDING_BOTTOM}px; text-align: left;"
        )

        # Zoom slider
        self._zoom_label.setStyleSheet(
            f"color: {t.text_secondary}; font-size: {S.FONT_LABEL}px; font-weight: 500;")
        self._zoom_slider.setStyleSheet(
            f"QSlider::groove:horizontal {{ background: {t.border}; height: {S.SLIDER_GROOVE_H}px; }}"
            f"QSlider::handle:horizontal {{ background: {t.text_secondary}; "
            f"width: {S.SLIDER_HANDLE_W}px; margin: -{S.SLIDER_HANDLE_MARGIN}px 0; }}"
        )

        self._cache_size_label.setStyleSheet(
            f"color: {t.text_hint}; font-size: {S.FONT_LABEL}px;")

        # Refresh icon colors — muted to match mockup
        for btn, icon in [
            (self._clear_btn, Icons.ERASER),
            (self._cache_btn, Icons.TRASH),
        ]:
            btn.setIcon(qta.icon(icon, color=t.text_hint))

        self._zoom_out_btn.setIcon(qta.icon(Icons.ZOOM_OUT, color=t.text_hint))
        self._zoom_in_btn.setIcon(qta.icon(Icons.ZOOM_IN, color=t.text_hint))

        _shuf_color = t.accent if self._shuffle else t.text_hint
        self._shuffle_btn.setIcon(qta.icon(Icons.SHUFFLE, color=_shuf_color))

        self._update_view_buttons()
        self._update_cache_size()

    # ------------------------------------------------------------------
    # View mode
    # ------------------------------------------------------------------

    def _set_view_mode(self, mode):
        self._view_mode = mode
        if mode == "list":
            self._stack.setCurrentWidget(self._list_scroll)
        else:
            self._stack.setCurrentWidget(self._grid_scroll)
        self._update_view_buttons()
        self._update_bottom_controls()
        self._rebuild()

    def _update_view_buttons(self):
        t = self.theme
        active_color = t.text_secondary
        inactive_color = t.text_hint
        list_color = active_color if self._view_mode == "list" else inactive_color
        grid_color = active_color if self._view_mode == "grid" else inactive_color
        self._list_btn.setIcon(qta.icon(Icons.LIST, color=list_color))
        self._grid_btn.setIcon(qta.icon(Icons.GRID, color=grid_color))

    def _update_bottom_controls(self):
        is_grid = self._view_mode == "grid"
        self._zoom_out_btn.setVisible(is_grid)
        self._zoom_in_btn.setVisible(is_grid)

    # ------------------------------------------------------------------
    # Restyle (theme change without full rebuild)
    # ------------------------------------------------------------------

    def _restyle_groups(self):
        """Update styles on existing group headers and lists without rebuilding."""
        for header, lw in self._list_groups:
            is_reserve = header.property("is_reserve")
            header.setStyleSheet(
                self._header_reserve_style if is_reserve else self._header_style)
            lw.setStyleSheet(self._list_style)
        for header, grid in self._grid_groups:
            is_reserve = header.property("is_reserve")
            header.setStyleSheet(
                self._header_reserve_style if is_reserve else self._header_style)

    # ------------------------------------------------------------------
    # Group expand/collapse
    # ------------------------------------------------------------------

    def _toggle_group(self, timer_val, widget):
        """Toggle a group body's visibility and remember the state."""
        new_visible = not widget.isVisible()
        widget.setVisible(new_visible)
        if new_visible:
            self._collapsed_tiers.discard(timer_val)
        else:
            self._collapsed_tiers.add(timer_val)

    # ------------------------------------------------------------------
    # Rebuild
    # ------------------------------------------------------------------

    def _rebuild(self):
        if self._loader and self._loader.isRunning():
            self._loader.loaded.disconnect(self._on_pixmap_loaded)
            self._loader.cancel()
            self._loader.wait()

        if self._view_mode == "list":
            self._rebuild_list()
        else:
            self._rebuild_grid()

        # Background load for uncached images
        uncached = [img.path for img in self.images if img.path not in self._pix_cache]
        if uncached:
            self._loader = PixmapLoader(uncached)
            self._loader.loaded.connect(self._on_pixmap_loaded)
            self._loader.start()

    def _rebuild_list(self):
        # Clear existing groups
        for header, lw in self._list_groups:
            header.hide()
            lw.hide()
            header.deleteLater()
            lw.deleteLater()
        self._list_groups = []

        ordered = self._ordered_groups()

        insert_pos = 0
        for timer_val, items in ordered:
            items = _sort_group_items(items)
            is_reserve = timer_val == 0
            if is_reserve:
                header_text = f"Reserve · {len(items)}"
                header_style = self._header_reserve_style
            else:
                header_text = f"{_short_label(timer_val)} · {len(items)}"
                header_style = self._header_style

            header = QPushButton(header_text, self._list_container)
            header.setProperty("is_reserve", is_reserve)
            header.setStyleSheet(header_style)
            header.setCursor(Qt.CursorShape.PointingHandCursor)
            header.setCheckable(False)

            lw = QListWidget(self._list_container)
            lw.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            lw.setDragDropMode(QListWidget.DragDropMode.InternalMove)
            lw.setDefaultDropAction(Qt.DropAction.MoveAction)
            lw.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
            lw.setIconSize(QSize(24, 24))
            lw.setStyleSheet(self._list_style)
            lw.model().rowsMoved.connect(self._on_reorder)

            t = self.theme
            for idx, img in items:
                name = self._short_name(img.path)
                pinned = getattr(img, "pinned", False)
                pin_prefix = "\u2022 " if pinned else ""   # bullet = pinned indicator
                if is_reserve:
                    timer_str = "—"
                else:
                    timer_str = format_time(img.timer)
                text = f"{idx + 1}.  {pin_prefix}{name}    {timer_str}"
                item = QListWidgetItem(text)

                pix = self._get_pixmap(img.path)
                if not pix.isNull():
                    item.setIcon(QIcon(pix))

                item.setData(Qt.ItemDataRole.UserRole, idx)

                if pinned:
                    item.setForeground(QBrush(QColor(t.accent)))
                elif is_reserve:
                    item.setForeground(QBrush(QColor(t.text_hint)))
                else:
                    item.setForeground(QBrush(QColor(t.text_primary)))

                lw.addItem(item)

            lw.setFixedHeight(len(items) * S.LIST_ITEM_H + S.LIST_PADDING)

            # Context menu for pin / move-to-group
            lw.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            lw.customContextMenuRequested.connect(
                lambda pos, w=lw: self._show_context_menu(pos, w))

            lw.setVisible(timer_val not in self._collapsed_tiers)
            header.clicked.connect(
                lambda checked, tv=timer_val, w=lw: self._toggle_group(tv, w))

            self._list_layout.insertWidget(insert_pos, header)
            self._list_layout.insertWidget(insert_pos + 1, lw)
            self._list_groups.append((header, lw))
            insert_pos += 2

    def _rebuild_grid(self):
        self._selected_tiles.clear()
        for header, grid in self._grid_groups:
            header.hide()
            grid.hide()
            header.deleteLater()
            grid.deleteLater()
        self._grid_groups = []

        groups = self._group_by_timer()
        non_reserve = sorted(
            [(tv, items) for tv, items in groups.items() if tv != 0],
            key=lambda g: g[0])
        reserve = [(tv, items) for tv, items in groups.items() if tv == 0]
        ordered = non_reserve + reserve

        sz = self._zoom_slider.value()
        insert_pos = 0
        t = self.theme

        for timer_val, items in ordered:
            items = _sort_group_items(items)
            is_reserve = timer_val == 0
            if is_reserve:
                header_text = f"Reserve · {len(items)}"
                header_style = self._header_reserve_style
            else:
                header_text = f"{_short_label(timer_val)} · {len(items)}"
                header_style = self._header_style

            header = QPushButton(header_text, self._grid_container)
            header.setProperty("is_reserve", is_reserve)
            header.setStyleSheet(header_style)
            header.setCursor(Qt.CursorShape.PointingHandCursor)

            grid = QWidget(self._grid_container)
            labels = []
            for idx, img in items:
                lbl = ClickableLabel(grid)
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

                pix = self._get_pixmap(img.path)
                if not pix.isNull():
                    scaled = pix.scaled(
                        sz, sz,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                    # Clip to rounded rect
                    rounded = QPixmap(scaled.size())
                    rounded.fill(QColor(0, 0, 0, 0))
                    rp = QPainter(rounded)
                    rp.setRenderHint(QPainter.RenderHint.Antialiasing)
                    rpath = QPainterPath()
                    rpath.addRoundedRect(QRectF(rounded.rect()), S.GRID_TILE_RADIUS, S.GRID_TILE_RADIUS)
                    rp.setClipPath(rpath)
                    rp.drawPixmap(0, 0, scaled)
                    rp.end()
                    lbl.setPixmap(rounded)

                lbl.setProperty("img_idx", idx)
                lbl.setToolTip(os.path.basename(img.path))

                # Border style per state — all tiles get rounded corners
                pinned = getattr(img, "pinned", False)
                if is_reserve:
                    lbl.setStyleSheet(f"border: {S.EDITOR_BORDER_DASHED}px dashed {t.text_hint};")
                else:
                    lbl.setStyleSheet("border: none;")

                # Pin icon overlay — right side, scales with tile size
                if pinned:
                    pin_sz = max(8, min(20, int(sz * 0.18)))
                    pin_overlay = QLabel(lbl)
                    pin_overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
                    pin_overlay.setFixedSize(pin_sz + S.PIN_OVERLAY_PADDING, pin_sz + S.PIN_OVERLAY_PADDING)
                    pin_icon = qta.icon(Icons.TOPMOST_ON, color=t.text_hint)
                    pin_overlay.setPixmap(pin_icon.pixmap(pin_sz, pin_sz))
                    pin_overlay.setStyleSheet("border: none; background: transparent;")
                    # Position after label is sized by flow layout
                    lbl._pin_overlay = pin_overlay
                    lbl._pin_sz = pin_sz

                labels.append(lbl)

            w = max(self._grid_scroll.viewport().width(), 200)
            h = _flow_position(labels, w, sz)
            # Position pin overlays now that labels are sized
            for lbl in labels:
                po = getattr(lbl, '_pin_overlay', None)
                if po:
                    psz = lbl._pin_sz
                    po.move(lbl.width() - psz - S.PIN_POS_X_OFFSET, S.PIN_POS_Y_OFFSET)
            grid.setFixedHeight(h)
            grid._labels = labels

            grid.setVisible(timer_val not in self._collapsed_tiers)
            header.clicked.connect(
                lambda checked, tv=timer_val, g=grid: self._toggle_group(tv, g))

            self._grid_layout.insertWidget(insert_pos, header)
            self._grid_layout.insertWidget(insert_pos + 1, grid)
            self._grid_groups.append((header, grid))
            insert_pos += 2

    # ------------------------------------------------------------------
    # Pixmap helpers
    # ------------------------------------------------------------------

    def _get_pixmap(self, path):
        pix = self._pix_cache.get(path)
        if pix is None:
            pix = QPixmap(path)
            if not pix.isNull():
                pix = pix.scaled(
                    S.GRID_MAX, S.GRID_MAX,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            self._pix_cache[path] = pix
        return pix

    def _on_pixmap_loaded(self, path, image):
        pix = QPixmap.fromImage(image)
        self._pix_cache[path] = pix

        if self._view_mode == "list":
            for _, lw in self._list_groups:
                for j in range(lw.count()):
                    item = lw.item(j)
                    idx = item.data(Qt.ItemDataRole.UserRole)
                    if (idx is not None and idx < len(self.images)
                            and self.images[idx].path == path):
                        item.setIcon(QIcon(pix))
        else:
            sz = self._zoom_slider.value()
            for _, grid in self._grid_groups:
                for lbl in getattr(grid, "_labels", []):
                    idx = lbl.property("img_idx")
                    if (idx is not None and idx < len(self.images)
                            and self.images[idx].path == path):
                        scaled = pix.scaled(
                            sz, sz,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                        lbl.setPixmap(scaled)
            self._reflow_grid()

    @staticmethod
    def _short_name(path, max_len=16):
        name = os.path.basename(path)
        if len(name) <= max_len:
            return name
        stem, ext = os.path.splitext(name)
        keep = max_len - len(ext) - 1
        if keep < 2:
            return name[:max_len]
        left = (keep + 1) // 2
        right = keep - left
        return stem[:left] + "\u2026" + stem[-right:] + ext

    # ------------------------------------------------------------------
    # Grouping
    # ------------------------------------------------------------------

    def _group_by_timer(self):
        groups = OrderedDict()
        for i, img in enumerate(self.images):
            key = img.timer
            if key not in groups:
                groups[key] = []
            groups[key].append((i, img))
        return groups

    def _ordered_groups(self):
        """Groups sorted by timer (shortest first), reserve last."""
        groups = self._group_by_timer()
        non_reserve = sorted(
            [(tv, items) for tv, items in groups.items() if tv != 0],
            key=lambda g: g[0])
        reserve = [(tv, items) for tv, items in groups.items() if tv == 0]
        return non_reserve + reserve

    # ------------------------------------------------------------------
    # Cache
    # ------------------------------------------------------------------

    def _update_cache_size(self):
        size = CacheManager().size()
        if size > 0:
            self._cache_btn.setVisible(True)
            self._cache_size_label.setText(CacheManager.format_size(size))
            self._cache_size_label.setVisible(True)
        else:
            self._cache_btn.setVisible(False)
            self._cache_size_label.setVisible(False)

    def _clear_cache(self):
        CacheManager().clear()
        self._update_cache_size()

    # ------------------------------------------------------------------
    # Zoom
    # ------------------------------------------------------------------

    def _on_zoom(self, value):
        if not self._grid_groups:
            return
        w = max(self._grid_scroll.viewport().width(), 200)
        for _, grid in self._grid_groups:
            labels = getattr(grid, "_labels", [])
            for lbl in labels:
                idx = lbl.property("img_idx")
                if idx is not None and idx < len(self.images):
                    pix = self._get_pixmap(self.images[idx].path)
                    if not pix.isNull():
                        scaled = pix.scaled(
                            value, value,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                        # Clip to rounded rect
                        rounded = QPixmap(scaled.size())
                        rounded.fill(QColor(0, 0, 0, 0))
                        rp = QPainter(rounded)
                        rp.setRenderHint(QPainter.RenderHint.Antialiasing)
                        rpath = QPainterPath()
                        rpath.addRoundedRect(QRectF(rounded.rect()), S.GRID_TILE_RADIUS, S.GRID_TILE_RADIUS)
                        rp.setClipPath(rpath)
                        rp.drawPixmap(0, 0, scaled)
                        rp.end()
                        lbl.setPixmap(rounded)
                # Update pin overlay size and position
                po = getattr(lbl, '_pin_overlay', None)
                if po:
                    pin_sz = max(8, min(20, int(value * 0.18)))
                    t = self.theme
                    pin_icon = qta.icon(Icons.TOPMOST_ON, color=t.text_hint)
                    po.setPixmap(pin_icon.pixmap(pin_sz, pin_sz))
                    po.setFixedSize(pin_sz + S.PIN_OVERLAY_PADDING, pin_sz + S.PIN_OVERLAY_PADDING)
                    lbl._pin_sz = pin_sz
            h = _flow_position(labels, w, value)
            grid.setFixedHeight(h)
            # Reposition pins after flow
            for lbl in labels:
                po = getattr(lbl, '_pin_overlay', None)
                if po:
                    po.move(lbl.width() - lbl._pin_sz - S.PIN_POS_X_OFFSET, S.PIN_POS_Y_OFFSET)

    def _reflow_grid(self):
        if self._view_mode != "grid" or not self._grid_groups:
            return
        sz = self._zoom_slider.value()
        w = max(self._grid_scroll.viewport().width(), 200)
        for _, grid in self._grid_groups:
            labels = getattr(grid, "_labels", [])
            if labels and grid.isVisible():
                h = _flow_position(labels, w, sz)
                grid.setFixedHeight(h)
                for lbl in labels:
                    po = getattr(lbl, '_pin_overlay', None)
                    if po:
                        psz = lbl._pin_sz
                        po.move(lbl.width() - psz - S.PIN_POS_X_OFFSET, S.PIN_POS_Y_OFFSET)

    # ------------------------------------------------------------------
    # Grid tile selection
    # ------------------------------------------------------------------

    def _get_all_tile_labels(self):
        all_labels = []
        for _, grid in self._grid_groups:
            all_labels.extend(getattr(grid, "_labels", []))
        return all_labels

    def _select_tile(self, lbl):
        t = self.theme
        self._selected_tiles.add(lbl)
        lbl._selected = True
        lbl.setStyleSheet(f"border: {S.EDITOR_BORDER_SELECTED}px solid {t.border_active};")

    def _deselect_tile(self, lbl):
        self._selected_tiles.discard(lbl)
        lbl._selected = False
        # Restore original border state
        idx = lbl.property("img_idx")
        if idx is not None and idx < len(self.images):
            img = self.images[idx]
            t = self.theme
            pinned = getattr(img, "pinned", False)
            is_reserve = img.timer == 0
            if is_reserve:
                lbl.setStyleSheet(f"border: {S.EDITOR_BORDER_DASHED}px dashed {t.text_hint};")
            else:
                lbl.setStyleSheet("border: none;")
        else:
            lbl.setStyleSheet("")

    def _on_tile_click(self, lbl, ctrl, shift=False):
        if shift and self._last_clicked_tile is not None:
            all_labels = self._get_all_tile_labels()
            try:
                idx_a = all_labels.index(self._last_clicked_tile)
                idx_b = all_labels.index(lbl)
            except ValueError:
                idx_a, idx_b = None, None
            if idx_a is not None and idx_b is not None:
                lo, hi = min(idx_a, idx_b), max(idx_a, idx_b)
                if not ctrl:
                    for old in list(self._selected_tiles):
                        self._deselect_tile(old)
                for i in range(lo, hi + 1):
                    self._select_tile(all_labels[i])
                self._last_clicked_tile = lbl
                return

        if ctrl:
            if lbl in self._selected_tiles:
                self._deselect_tile(lbl)
            else:
                self._select_tile(lbl)
        else:
            for old in list(self._selected_tiles):
                self._deselect_tile(old)
            self._select_tile(lbl)
        self._last_clicked_tile = lbl

    # ------------------------------------------------------------------
    # Context menus (pin / move to group)
    # ------------------------------------------------------------------

    def _build_img_menu(self, img):
        """Build styled context menu with pin toggle and 'Move to...' submenu."""
        from PyQt6.QtWidgets import QMenu
        t = self.theme
        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu {{ background-color: {t.bg_button}; color: {t.text_primary}; "
            f"border: 1px solid {t.border}; font-size: {S.FONT_BUTTON}px; }}"
            f"QMenu::item:selected {{ background-color: {t.bg_active}; }}"
        )

        pinned = getattr(img, "pinned", False)
        pin_action = menu.addAction("Unpin" if pinned else "Pin to group")

        # "Move to..." submenu — all configured tiers + existing groups
        move_menu = menu.addMenu("Move to...")
        groups = self._group_by_timer()
        seen = set()
        for timer_val in sorted(self._all_tier_timers):
            if timer_val == img.timer:
                continue
            label = "Reserve" if timer_val == 0 else format_time(timer_val)
            act = move_menu.addAction(label)
            act.setData(timer_val)
            seen.add(timer_val)
        for timer_val in groups.keys():
            if timer_val in seen or timer_val == img.timer:
                continue
            label = "Reserve" if timer_val == 0 else format_time(timer_val)
            act = move_menu.addAction(label)
            act.setData(timer_val)
            seen.add(timer_val)
        if 0 not in seen and img.timer != 0:
            act = move_menu.addAction("Reserve")
            act.setData(0)

        return menu, pin_action

    def _handle_menu_action(self, img, action, pin_action):
        """Handle result from _build_img_menu. Returns True if something changed."""
        if action == pin_action:
            img.pinned = not getattr(img, "pinned", False)
        elif action is not None and action.data() is not None:
            img.timer = action.data()
            img.pinned = True
        else:
            return False
        self._rebuild()
        self._emit()
        return True

    def _show_context_menu(self, pos, list_widget):
        item = list_widget.itemAt(pos)
        if item is None:
            return
        idx = item.data(Qt.ItemDataRole.UserRole)
        if idx is None or idx >= len(self.images):
            return
        img = self.images[idx]
        menu, pin_action = self._build_img_menu(img)
        action = menu.exec(list_widget.mapToGlobal(pos))
        self._handle_menu_action(img, action, pin_action)

    def _show_tile_context_menu(self, tile, global_pos):
        idx = tile.property("img_idx")
        if idx is None or idx >= len(self.images):
            return
        img = self.images[idx]
        menu, pin_action = self._build_img_menu(img)
        action = menu.exec(global_pos)
        self._handle_menu_action(img, action, pin_action)

    # ------------------------------------------------------------------
    # Reorder
    # ------------------------------------------------------------------

    def _on_reorder(self):
        new_order = []
        for _, lw in self._list_groups:
            for i in range(lw.count()):
                item = lw.item(i)
                orig_idx = item.data(Qt.ItemDataRole.UserRole)
                if orig_idx is not None and orig_idx < len(self.images):
                    new_order.append(self.images[orig_idx])
        if new_order:
            self.images = new_order
            self._rebuild()
            self._emit()

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def _delete_selected(self):
        indices_to_remove = set()
        if self._view_mode == "list":
            for _, lw in self._list_groups:
                for ix in lw.selectedIndexes():
                    item = lw.item(ix.row())
                    orig = item.data(Qt.ItemDataRole.UserRole)
                    if orig is not None:
                        indices_to_remove.add(orig)
        else:
            for lbl in self._selected_tiles:
                idx = lbl.property("img_idx")
                if idx is not None:
                    indices_to_remove.add(idx)
            self._selected_tiles.clear()
        for i in sorted(indices_to_remove, reverse=True):
            if 0 <= i < len(self.images):
                self.images.pop(i)
        if indices_to_remove:
            self._rebuild()
            self._emit()

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _add_files(self):
        exts = " ".join(f"*{e}" for e in SUPPORTED_FORMATS)
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select files", "",
            f"Images ({exts});;All files (*)",
        )
        if paths:
            for p in filter_image_files(paths):
                self.images.append(ImageItem(path=p, timer=300))
            self._rebuild()
            self._emit()

    def _add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select folder")
        if folder:
            for p in scan_folder(folder):
                self.images.append(ImageItem(path=p, timer=300))
            self._rebuild()
            self._emit()

    def _add_from_url(self):
        from ui.url_dialog import UrlDialog
        timer = 300
        if self._parent and hasattr(self._parent, "get_timer_seconds"):
            timer = self._parent.get_timer_seconds()
        dlg = UrlDialog(self.theme, timer=timer, parent=self)
        dlg.images_loaded.connect(self._on_url_images)
        dlg.exec()

    def _on_url_images(self, images):
        for img in images:
            self.images.append(img)
        self._pix_cache.clear()
        self._rebuild()
        self._emit()
        self._update_cache_size()

    def _toggle_shuffle(self):
        self._shuffle = not self._shuffle
        t = self.theme
        color = t.accent if self._shuffle else t.text_hint
        self._shuffle_btn.setIcon(qta.icon(Icons.SHUFFLE, color=color))
        self.shuffle_changed.emit(self._shuffle)

    def _clear(self):
        if not self.images:
            return
        msg = QMessageBox(self)
        msg.setWindowTitle("Clear")
        msg.setText(f"Remove all {len(self.images)} files from list?")
        msg.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.No)
        t = self.theme
        msg.setStyleSheet(
            f"background-color: {t.bg}; color: {t.text_primary}; font-size: {S.FONT_MSG_BOX}px;")
        if msg.exec() != QMessageBox.StandardButton.Yes:
            return
        self.images = []
        self._rebuild()
        self._emit()

    # ------------------------------------------------------------------
    # Drag-and-drop onto scroll area
    # ------------------------------------------------------------------

    def _drag_enter(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def _drop_event(self, event):
        urls = event.mimeData().urls()
        added = False
        for url in urls:
            if url.isLocalFile():
                path = url.toLocalFile()
                if os.path.isdir(path):
                    for p in scan_folder(path):
                        self.images.append(ImageItem(path=p, timer=300))
                        added = True
                elif any(path.lower().endswith(e) for e in SUPPORTED_FORMATS):
                    self.images.append(ImageItem(path=path, timer=300))
                    added = True
        if added:
            self._rebuild()
            self._emit()

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------

    def _emit(self):
        self.images_updated.emit(self.images)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def refresh(self, images):
        """Update file list from parent; clears pix cache if paths changed."""
        old_paths = {img.path for img in self.images}
        self.images = list(images)
        new_paths = {img.path for img in self.images}
        if old_paths != new_paths:
            self._pix_cache.clear()
        self._rebuild()

    # ------------------------------------------------------------------
    # Qt events
    # ------------------------------------------------------------------

    def showEvent(self, event):
        super().showEvent(event)
        if self._needs_initial_rebuild:
            self._needs_initial_rebuild = False
            QTimer.singleShot(10, self._rebuild)
        else:
            self._reflow_grid()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reflow_grid()

    def eventFilter(self, obj, event):
        if (event.type() == event.Type.Wheel
                and event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            delta = event.angleDelta().y()
            step = S.GRID_ZOOM_STEP if delta > 0 else -S.GRID_ZOOM_STEP
            slider = self._zoom_slider
            slider.setValue(
                max(slider.minimum(), min(slider.value() + step, slider.maximum()))
            )
            return True  # consumed — don't let scroll area scroll
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            self._delete_selected()
        else:
            super().keyPressEvent(event)
