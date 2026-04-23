# ui/editor_panel/__init__.py
"""EditorPanel package — split for maintainability.

Public surface: EditorPanel (the widget) plus the pure helpers unit-tested
directly from tests/. Everything else is package-internal; callers should
import from sibling modules.
"""

from ui.editor_panel.tile_drag import (
    _compute_insertion_index,
    _filter_selection_by_zone,
    _apply_tile_drop,
)
from ui.editor_panel.sort import _sort_group_items
from ui.editor_panel.panel import EditorPanel

__all__ = [
    "EditorPanel",
    "_sort_group_items",
    "_compute_insertion_index",
    "_filter_selection_by_zone",
    "_apply_tile_drop",
]
