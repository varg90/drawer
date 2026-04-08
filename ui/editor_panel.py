# ui/editor_panel.py
"""EditorPanel — reusable image editor panel widget for RefBot.

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
from PyQt6.QtGui import QPixmap, QIcon, QColor, QBrush, QImage
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer, QThread

from core.constants import SUPPORTED_FORMATS
from core.file_utils import filter_image_files, scan_folder
from core.models import ImageItem
from core.timer_logic import format_time
from core.cloud.cache import CacheManager
from ui.scales import S
from ui.icons import Icons
from ui.widgets import make_icon_btn

GRID_MIN = 48
GRID_MAX = 256
GRID_DEFAULT = 80


# ---------------------------------------------------------------------------
# Background image loader (reused from image_editor_window.py)
# ---------------------------------------------------------------------------

class PixmapLoader(QThread):
    """Load images from disk in a background thread."""
    loaded = pyqtSignal(str, QImage)

    def __init__(self, paths, max_size=GRID_MAX):
        super().__init__()
        self._paths = paths
        self._max = max_size
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
        editor = self.window()
        if not hasattr(editor, "_on_tile_click"):
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
    detach_requested = pyqtSignal()

    def __init__(self, images, theme, parent=None, view_mode="list"):
        super().__init__(parent)
        self.images = list(images)
        self.theme = theme
        self._parent = parent
        self._view_mode = view_mode if view_mode in ("list", "grid") else "list"

        self._pix_cache = {}          # path -> QPixmap
        self._loader = None           # PixmapLoader thread
        self._selected_tiles = set()  # set of ClickableLabel
        self._last_clicked_tile = None

        self._list_groups = []   # list of (header_btn, list_widget)
        self._grid_groups = []   # list of (header_btn, grid_widget)

        self._needs_initial_rebuild = True

        self._build_ui()
        self._apply_theme()
        self._set_view_mode(self._view_mode)

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 8)
        root.setSpacing(6)

        # --- Toolbar ---
        toolbar = QHBoxLayout()
        toolbar.setSpacing(4)
        toolbar.setContentsMargins(0, 0, 0, 0)

        self._add_files_btn = make_icon_btn(
            Icons.ADD_FILE, self.theme.text_secondary,
            size=S.EDITOR_BTN, tooltip="Add files",
        )
        self._add_files_btn.clicked.connect(self._add_files)

        self._add_folder_btn = make_icon_btn(
            Icons.ADD_FOLDER, self.theme.text_secondary,
            size=S.EDITOR_BTN, tooltip="Add folder",
        )
        self._add_folder_btn.clicked.connect(self._add_folder)

        self._url_btn = make_icon_btn(
            Icons.ADD_URL, self.theme.text_secondary,
            size=S.EDITOR_BTN, tooltip="Load from URL",
        )
        self._url_btn.clicked.connect(self._add_from_url)

        self._detach_btn = make_icon_btn(
            Icons.DETACH, self.theme.text_secondary,
            size=S.EDITOR_BTN, tooltip="Detach to window",
        )
        self._detach_btn.clicked.connect(self.detach_requested.emit)

        toolbar.addWidget(self._add_files_btn)
        toolbar.addWidget(self._add_folder_btn)
        toolbar.addWidget(self._url_btn)
        toolbar.addWidget(self._detach_btn)
        toolbar.addStretch()

        self._clear_btn = make_icon_btn(
            Icons.ERASER, self.theme.text_secondary,
            size=S.EDITOR_BTN, tooltip="Clear all",
        )
        self._clear_btn.clicked.connect(self._clear)

        self._close_btn = make_icon_btn(
            Icons.CLOSE, self.theme.text_secondary,
            size=S.EDITOR_BTN, tooltip="Close",
        )
        self._close_btn.clicked.connect(self.close_requested.emit)

        toolbar.addWidget(self._clear_btn)
        toolbar.addWidget(self._close_btn)

        root.addLayout(toolbar)

        # --- Count label ---
        self._count_label = QLabel("")
        root.addWidget(self._count_label)

        # --- Stacked widget: list / grid ---
        self._stack = QStackedWidget()

        # List scroll
        self._list_scroll = QScrollArea()
        self._list_scroll.setWidgetResizable(True)
        self._list_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list_scroll.setAcceptDrops(True)
        self._list_scroll.dragEnterEvent = self._drag_enter
        self._list_scroll.dropEvent = self._drop_event

        self._list_container = QWidget()
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(4)
        self._list_layout.addStretch()
        self._list_scroll.setWidget(self._list_container)
        self._stack.addWidget(self._list_scroll)

        # Grid scroll
        self._grid_scroll = QScrollArea()
        self._grid_scroll.setWidgetResizable(True)
        self._grid_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._grid_scroll.setAcceptDrops(True)
        self._grid_scroll.dragEnterEvent = self._drag_enter
        self._grid_scroll.dropEvent = self._drop_event

        self._grid_container = QWidget()
        self._grid_layout = QVBoxLayout(self._grid_container)
        self._grid_layout.setContentsMargins(0, 0, 0, 0)
        self._grid_layout.setSpacing(4)
        self._grid_layout.addStretch()
        self._grid_scroll.setWidget(self._grid_container)
        self._stack.addWidget(self._grid_scroll)

        root.addWidget(self._stack, 1)

        # --- Bottom controls ---
        bottom = QHBoxLayout()
        bottom.setSpacing(4)
        bottom.setContentsMargins(0, 0, 0, 0)

        # List/grid toggle
        self._list_btn = make_icon_btn(
            Icons.LIST, self.theme.text_secondary,
            size=S.EDITOR_BTN, tooltip="List view",
        )
        self._list_btn.clicked.connect(lambda: self._set_view_mode("list"))

        self._grid_btn = make_icon_btn(
            Icons.GRID, self.theme.text_secondary,
            size=S.EDITOR_BTN, tooltip="Grid view",
        )
        self._grid_btn.clicked.connect(lambda: self._set_view_mode("grid"))

        bottom.addWidget(self._list_btn)
        bottom.addWidget(self._grid_btn)

        # Zoom slider (grid mode only)
        self._zoom_label = QLabel("Zoom:")
        bottom.addWidget(self._zoom_label)

        self._zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self._zoom_slider.setRange(GRID_MIN, GRID_MAX)
        self._zoom_slider.setValue(GRID_DEFAULT)
        self._zoom_slider.setFixedWidth(90)
        self._zoom_slider.valueChanged.connect(self._on_zoom)
        bottom.addWidget(self._zoom_slider)

        bottom.addStretch()

        # Cache trash + size
        self._cache_btn = make_icon_btn(
            Icons.TRASH, self.theme.text_secondary,
            size=S.EDITOR_BTN, tooltip="Clear cache",
        )
        self._cache_btn.clicked.connect(self._clear_cache)
        self._cache_size_label = QLabel("")
        bottom.addWidget(self._cache_btn)
        bottom.addWidget(self._cache_size_label)

        root.addLayout(bottom)

        # --- Total label ---
        self._total_label = QLabel("")
        root.addWidget(self._total_label)

        self._update_bottom_controls()

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------

    def _apply_theme(self):
        t = self.theme
        self.setStyleSheet(f"background-color: {t.bg}; color: {t.text_primary};")

        self._count_label.setStyleSheet(
            f"color: {t.text_secondary}; font-size: {S.FONT_BUTTON}px; "
            f"font-weight: 500; letter-spacing: 2px;")

        self._total_label.setStyleSheet(
            f"color: {t.text_secondary}; font-size: {S.FONT_LABEL}px;")

        # Scroll area backgrounds + dashed drop-target border
        # Use #id selector to avoid bleeding into child widgets
        self._list_scroll.setObjectName("editorListScroll")
        self._grid_scroll.setObjectName("editorGridScroll")
        self._list_container.setObjectName("editorListContainer")
        self._grid_container.setObjectName("editorGridContainer")
        scroll_s = (
            f"QScrollArea#editorListScroll, QScrollArea#editorGridScroll {{ "
            f"background-color: {t.bg_secondary}; border: 1px dashed {t.border}; }}"
        )
        container_s = (
            f"QWidget#editorListContainer, QWidget#editorGridContainer {{ "
            f"background-color: {t.bg_secondary}; }}"
        )
        self._list_scroll.setStyleSheet(scroll_s)
        self._grid_scroll.setStyleSheet(scroll_s)
        self._list_container.setStyleSheet(container_s)
        self._grid_container.setStyleSheet(container_s)

        # Styles stored for reuse in rebuild
        self._list_style = (
            f"QListWidget {{ background-color: {t.bg_secondary}; border: none; "
            f"font-size: {S.FONT_BUTTON}px; color: {t.text_primary}; }}"
            f"QListWidget::item {{ padding: 2px; }}"
            f"QListWidget::item:selected {{ background-color: {t.bg_active}; }}"
        )
        self._header_style = (
            f"background-color: {t.bg_button}; color: {t.text_secondary}; "
            f"border: 1px solid {t.border}; font-size: {S.FONT_BUTTON}px; "
            f"font-weight: 500; padding: 2px 8px; text-align: left;"
        )
        self._header_reserve_style = (
            f"background-color: {t.bg_button}; color: {t.text_hint}; "
            f"border: 1px solid {t.border}; font-size: {S.FONT_BUTTON}px; "
            f"font-weight: 500; padding: 2px 8px; text-align: left;"
        )

        # Zoom slider
        self._zoom_label.setStyleSheet(
            f"color: {t.text_secondary}; font-size: {S.FONT_LABEL}px; font-weight: 500;")
        self._zoom_slider.setStyleSheet(
            f"QSlider::groove:horizontal {{ background: {t.border}; height: 4px; }}"
            f"QSlider::handle:horizontal {{ background: {t.text_secondary}; "
            f"width: 12px; margin: -4px 0; }}"
        )

        self._cache_size_label.setStyleSheet(
            f"color: {t.text_secondary}; font-size: {S.FONT_LABEL}px;")

        # Refresh icon colors
        for btn, icon in [
            (self._add_files_btn, Icons.ADD_FILE),
            (self._add_folder_btn, Icons.ADD_FOLDER),
            (self._url_btn, Icons.ADD_URL),
            (self._detach_btn, Icons.DETACH),
            (self._clear_btn, Icons.ERASER),
            (self._close_btn, Icons.CLOSE),
            (self._cache_btn, Icons.TRASH),
        ]:
            btn.setIcon(qta.icon(icon, color=t.text_secondary))

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
        active_color = t.text_primary
        inactive_color = t.text_secondary
        list_color = active_color if self._view_mode == "list" else inactive_color
        grid_color = active_color if self._view_mode == "grid" else inactive_color
        self._list_btn.setIcon(qta.icon(Icons.LIST, color=list_color))
        self._grid_btn.setIcon(qta.icon(Icons.GRID, color=grid_color))

    def _update_bottom_controls(self):
        is_grid = self._view_mode == "grid"
        self._zoom_label.setVisible(is_grid)
        self._zoom_slider.setVisible(is_grid)

    # ------------------------------------------------------------------
    # Rebuild
    # ------------------------------------------------------------------

    def _rebuild(self):
        if self._loader and self._loader.isRunning():
            self._loader.cancel()
            self._loader.wait()

        if self._view_mode == "list":
            self._rebuild_list()
        else:
            self._rebuild_grid()

        n = len(self.images)
        self._count_label.setText(f"IMAGES — {n}")
        self._update_total_label()

        # Background load for uncached images
        uncached = [img.path for img in self.images if img.path not in self._pix_cache]
        if uncached:
            self._loader = PixmapLoader(uncached)
            self._loader.loaded.connect(self._on_pixmap_loaded)
            self._loader.start()

    def _rebuild_list(self):
        # Clear existing groups
        for header, lw in self._list_groups:
            header.setParent(None)
            lw.setParent(None)
            header.deleteLater()
            lw.deleteLater()
        self._list_groups = []

        groups = self._group_by_timer()
        # Non-reserve groups first, reserve (timer=0) last
        non_reserve = [(tv, items) for tv, items in groups.items() if tv != 0]
        reserve = [(tv, items) for tv, items in groups.items() if tv == 0]
        ordered = non_reserve + reserve

        insert_pos = 0
        for timer_val, items in ordered:
            is_reserve = timer_val == 0
            if is_reserve:
                header_text = f"Reserve — {len(items)}"
                header_style = self._header_reserve_style
            else:
                header_text = f"{format_time(timer_val)} — {len(items)}"
                header_style = self._header_style

            header = QPushButton(header_text)
            header.setStyleSheet(header_style)
            header.setCursor(Qt.CursorShape.PointingHandCursor)
            header.setCheckable(False)

            lw = QListWidget()
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

            lw.setFixedHeight(len(items) * 30 + 4)

            # Reserve starts collapsed
            if is_reserve:
                lw.setVisible(False)

            header.clicked.connect(lambda checked, w=lw: w.setVisible(not w.isVisible()))

            self._list_layout.insertWidget(insert_pos, header)
            self._list_layout.insertWidget(insert_pos + 1, lw)
            self._list_groups.append((header, lw))
            insert_pos += 2

    def _rebuild_grid(self):
        self._selected_tiles.clear()
        for header, grid in self._grid_groups:
            header.setParent(None)
            grid.setParent(None)
            header.deleteLater()
            grid.deleteLater()
        self._grid_groups = []

        groups = self._group_by_timer()
        non_reserve = [(tv, items) for tv, items in groups.items() if tv != 0]
        reserve = [(tv, items) for tv, items in groups.items() if tv == 0]
        ordered = non_reserve + reserve

        sz = self._zoom_slider.value()
        insert_pos = 0
        t = self.theme

        for timer_val, items in ordered:
            is_reserve = timer_val == 0
            if is_reserve:
                header_text = f"Reserve — {len(items)}"
                header_style = self._header_reserve_style
            else:
                header_text = f"{format_time(timer_val)} — {len(items)}"
                header_style = self._header_style

            header = QPushButton(header_text)
            header.setStyleSheet(header_style)
            header.setCursor(Qt.CursorShape.PointingHandCursor)

            grid = QWidget()
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
                    lbl.setPixmap(scaled)

                lbl.setProperty("img_idx", idx)
                lbl.setToolTip(os.path.basename(img.path))

                # Border style per state
                pinned = getattr(img, "pinned", False)
                if pinned:
                    lbl.setStyleSheet(f"border: 2px solid {t.border_active};")
                elif is_reserve:
                    lbl.setStyleSheet(f"border: 1px dashed {t.text_hint};")
                else:
                    lbl.setStyleSheet("border: none;")

                labels.append(lbl)

            w = max(self._grid_scroll.viewport().width(), 200)
            h = _flow_position(labels, w, sz)
            grid.setFixedHeight(h)
            grid._labels = labels

            # Reserve starts collapsed
            if is_reserve:
                grid.setVisible(False)

            header.clicked.connect(lambda checked, g=grid: g.setVisible(not g.isVisible()))

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
                    GRID_MAX, GRID_MAX,
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
    def _short_name(path, max_len=22):
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

    # ------------------------------------------------------------------
    # Total label
    # ------------------------------------------------------------------

    def _update_total_label(self):
        t = self.theme
        # Sum only active (timer > 0) images
        total_s = sum(img.timer for img in self.images if img.timer > 0)

        # Get session duration from parent if available
        session_secs = 0
        if self._parent and hasattr(self._parent, '_get_session_seconds'):
            session_secs = self._parent._get_session_seconds()

        if total_s == 0:
            self._total_label.setText("")
            return

        # Format total time
        total_text = format_time(total_s)

        # Check if over budget
        is_over_budget = session_secs > 0 and total_s > session_secs

        if is_over_budget:
            # Show "total / session" with warning color
            session_text = format_time(session_secs)
            text = f"{total_text} / {session_text}"
            color = t.warning
        else:
            text = f"{total_text} total"
            color = t.text_secondary

        self._total_label.setText(text)
        self._total_label.setStyleSheet(
            f"color: {color}; font-size: {S.FONT_LABEL}px;")

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
                        lbl.setPixmap(scaled)
            h = _flow_position(labels, w, value)
            grid.setFixedHeight(h)

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
        lbl.setStyleSheet(f"border: 2px solid {t.border_active};")

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
            if pinned:
                lbl.setStyleSheet(f"border: 2px solid {t.border_active};")
            elif is_reserve:
                lbl.setStyleSheet(f"border: 1px dashed {t.text_hint};")
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
            f"background-color: {t.bg}; color: {t.text_primary}; font-size: 12px;")
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

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            self._delete_selected()
        else:
            super().keyPressEvent(event)
