# ui/editor_panel/__init__.py
"""EditorPanel package — split for maintainability.

Public surface preserved from the pre-split ui/editor_panel.py.
"""

from ui.editor_panel.tile_drag import (
    TILE_DRAG_MIME,
    _decode_tile_drag_payload,
    _compute_insertion_index,
    _filter_selection_by_zone,
    _apply_tile_drop,
)
from ui.editor_panel.flow_layout import _flow_position, _flow_position_with_gaps
from ui.editor_panel.sort import _sort_group_items
from ui.editor_panel.pixmap_loader import PixmapLoader
from ui.editor_panel.tile_widgets import (
    _ColorLine,
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
