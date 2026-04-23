# ui/editor_panel/tile_widgets.py
"""Tile widget classes: color line, clickable label, drop placeholders."""

import qtawesome as qta
from PyQt6.QtWidgets import QWidget, QLabel, QListWidget
from PyQt6.QtGui import QPixmap, QColor, QPainter
from PyQt6.QtCore import Qt

from ui.icons import Icons
from ui.scales import S
from ui.editor_panel.tile_drag import (
    TILE_DRAG_MIME,
    _decode_tile_drag_payload,
    _apply_tile_drop,
    _filter_selection_by_zone,
)


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


class ClickableLabel(QLabel):
    """QLabel with click-to-select + drag-source support for grid tiles."""

    DRAG_THRESHOLD = 5  # pixels

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected = False
        self._press_pos = None
        self._drag_started = False
        self._deferred_click = False

    def _find_editor(self):
        w = self.parent()
        while w is not None:
            if hasattr(w, "_on_tile_click"):
                return w
            w = w.parent()
        return None

    def mousePressEvent(self, event):
        editor = self._find_editor()
        if editor is None:
            return

        if event.button() == Qt.MouseButton.RightButton:
            editor._show_tile_context_menu(self, event.globalPosition().toPoint())
            return

        if event.button() != Qt.MouseButton.LeftButton:
            return

        self._press_pos = event.pos()
        self._drag_started = False

        mods = event.modifiers()
        ctrl = bool(mods & Qt.KeyboardModifier.ControlModifier)
        shift = bool(mods & Qt.KeyboardModifier.ShiftModifier)

        # If the tile is already in the selection and no modifier is held,
        # defer the click action until release — a plain click on a selected
        # tile normally collapses the selection to just that tile, but if the
        # user's about to drag a multi-selection, we must preserve it.
        if self in editor._selected_tiles and not ctrl and not shift:
            self._deferred_click = True
            return

        self._deferred_click = False
        editor._on_tile_click(self, ctrl, shift)

    def mouseMoveEvent(self, event):
        if self._press_pos is None or self._drag_started:
            return
        editor = self._find_editor()
        if editor is None or getattr(editor, "_timer_mode", "quick") != "quick":
            return
        if (event.pos() - self._press_pos).manhattanLength() < self.DRAG_THRESHOLD:
            return

        # Build the list of source indices: the selection if this tile is
        # part of it, else just this tile. Then filter to same-zone.
        my_idx = self.property("img_idx")
        if my_idx is None or my_idx >= len(editor.images):
            return
        my_is_pinned = bool(editor.images[my_idx].pinned)

        if self in editor._selected_tiles:
            # Set iteration order is undefined → sort so the dragged block
            # retains the user's list order when multi-select moves together.
            sel_indices = sorted(
                lbl.property("img_idx")
                for lbl in editor._selected_tiles
                if lbl.property("img_idx") is not None
            )
            indices = _filter_selection_by_zone(sel_indices, my_is_pinned,
                                                editor.images)
            if my_idx not in indices:
                indices = [my_idx]
        else:
            indices = [my_idx]

        self._drag_started = True
        self._deferred_click = False  # drag consumed the click
        editor._start_tile_drag(self, indices, my_is_pinned)

    def mouseReleaseEvent(self, event):
        # If the press was on an already-selected tile and no drag happened,
        # apply the plain-click behavior now (collapse selection to just this
        # tile), matching the pre-defer semantics for non-drag clicks.
        if self._deferred_click and not self._drag_started:
            editor = self._find_editor()
            if editor is not None:
                editor._on_tile_click(self, False, False)
        self._press_pos = None
        self._drag_started = False
        self._deferred_click = False


class _PinPlaceholderRow(QLabel):
    """A dashed-outline 'drop here to pin' row for the empty pinned zone in
    quick-mode list view."""

    def __init__(self, editor, theme, parent=None):
        super().__init__(parent)
        self._editor = editor
        self.setText("  drop here to pin  ")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(S.LIST_ITEM_H)
        self.setStyleSheet(
            f"border: 2px dashed {theme.text_hint}; "
            f"border-radius: {S.GRID_TILE_RADIUS}px; "
            f"color: {theme.text_hint}; "
            f"font-size: {S.FONT_BUTTON}px; "
            f"background: transparent;"
        )
        self.setAcceptDrops(True)

    def _is_acceptable_drag(self, event):
        # Accept either our custom tile-drag MIME (tile view) or a drag
        # sourced from one of the editor's list widgets (list view, which
        # uses Qt's built-in InternalMove with application/x-qabstractitem-
        # modeldatalist and doesn't carry TILE_DRAG_MIME).
        if event.mimeData().hasFormat(TILE_DRAG_MIME):
            return True
        src = event.source()
        for _, lw in self._editor._list_groups:
            if src is lw:
                return True
        return False

    def _read_source_indices(self, event):
        """Return source image indices for either drag type, or None."""
        if event.mimeData().hasFormat(TILE_DRAG_MIME):
            return _decode_tile_drag_payload(event.mimeData())
        src = event.source()
        if not isinstance(src, QListWidget):
            return None
        indices = []
        for i in range(src.count()):
            item = src.item(i)
            if not item.isSelected():
                continue
            idx = item.data(Qt.ItemDataRole.UserRole)
            if idx is not None and idx < len(self._editor.images):
                indices.append(idx)
        return indices or None

    def dragEnterEvent(self, event):
        if self._is_acceptable_drag(event):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if self._is_acceptable_drag(event):
            event.acceptProposedAction()

    def dropEvent(self, event):
        source_indices = self._read_source_indices(event)
        if not source_indices:
            event.ignore()
            return
        new_images = _apply_tile_drop(
            self._editor.images, source_indices, insert_idx=0,
            target_is_pinned=True,
        )
        self._editor.images = new_images
        self._editor._drag_insert_idx = None  # drop handler owns the rebuild
        self._editor._rebuild()
        self._editor._emit()
        event.acceptProposedAction()


class _PinPlaceholderTile(QLabel):
    """Dashed-outline placeholder for the empty pinned zone in tile view.
    Accepts internal tile drags; forwards to EditorPanel's drop logic."""

    def __init__(self, editor, size, theme, parent=None):
        super().__init__(parent)
        self._editor = editor
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(
            f"border: 2px dashed {theme.text_hint}; "
            f"border-radius: {S.GRID_TILE_RADIUS}px; "
            f"background: transparent;"
        )
        # Build a tile-sized transparent pixmap with the pin icon centered.
        pix = QPixmap(size, size)
        pix.fill(QColor(0, 0, 0, 0))
        icon_sz = max(16, int(size * 0.35))
        icon = qta.icon(Icons.TOPMOST_ON, color=theme.accent)
        icon_pix = icon.pixmap(icon_sz, icon_sz)
        p = QPainter(pix)
        p.drawPixmap(
            (size - icon_sz) // 2,
            (size - icon_sz) // 2,
            icon_pix,
        )
        p.end()
        self.setPixmap(pix)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(TILE_DRAG_MIME):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(TILE_DRAG_MIME):
            event.acceptProposedAction()

    def dropEvent(self, event):
        """Drop on placeholder = pin at index 0."""
        source_indices = _decode_tile_drag_payload(event.mimeData())
        if source_indices is None:
            event.ignore()
            return
        new_images = _apply_tile_drop(
            self._editor.images, source_indices, insert_idx=0,
            target_is_pinned=True,
        )
        self._editor.images = new_images
        self._editor._drag_insert_idx = None  # drop handler owns the rebuild
        self._editor._rebuild()
        self._editor._emit()
        event.acceptProposedAction()
