# ui/editor_panel/__init__.py
"""EditorPanel package — split for maintainability.

Public surface preserved from the pre-split ui/editor_panel.py.
"""

from ui.editor_panel.tile_drag import (
    TILE_DRAG_MIME,
    _compute_insertion_index,
    _filter_selection_by_zone,
    _apply_tile_drop,
)
from ui.editor_panel.sort import _sort_group_items
from ui.editor_panel.pixmap_loader import PixmapLoader
from ui.editor_panel.tile_widgets import (
    ClickableLabel,
    _PinPlaceholderRow,
    _PinPlaceholderTile,
)
from ui.editor_panel.panel import EditorPanel

__all__ = [
    "EditorPanel",
    "ClickableLabel",
    "PixmapLoader",
    "TILE_DRAG_MIME",
    "_sort_group_items",
    "_compute_insertion_index",
    "_filter_selection_by_zone",
    "_apply_tile_drop",
    "_PinPlaceholderRow",
    "_PinPlaceholderTile",
]
