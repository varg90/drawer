# Editor Panel Split — Design

**Date:** 2026-04-23
**Scope:** `ui/editor_panel.py` (1787 lines) → package `ui/editor_panel/` with focused modules.
**Goal:** Reduce file size and group related code. **No behavior change.**

## Motivation

`ui/editor_panel.py` has grown to 1787 lines and mixes five distinct concerns in one file:
drag-drop helpers, flow layout geometry, a `QThread` pixmap loader, four tile widget classes,
and the ~1290-line `EditorPanel` class itself. This is the first item in Bundle B (editor panel
cleanup). Splitting first creates cleaner seams for the follow-up fixes (O(N²) pixmap matching,
LRU cache cap, zoom persistence, zoom overflow).

## Non-goals

- Behavior changes of any kind.
- Renaming or modifying the public API.
- Extracting methods out of the `EditorPanel` class (deferred to Option B below).
- Addressing Bundle B items 2-5 (they land on separate branches after this).
- Adding new tests. Existing coverage is the safety net.

## Approach — Option A (pure mechanical split)

Relocate module-level helpers and the small widget classes into sibling modules inside a new
`ui/editor_panel/` package. `EditorPanel` itself stays intact in `panel.py`. A re-exporting
`__init__.py` preserves every import path in use today.

Option A was chosen over Option B (carve `EditorPanel` internals) because the state sharing
inside `EditorPanel` (`self.images`, `self.theme`, selection state, signals, viewport refs)
would force either explicit parameter threading or back-references through helper objects,
and the diff would be far harder to review. Option A delivers most of the maintainability
win at a fraction of the risk. Option B is sketched below as a candidate follow-up.

## Module layout

```
ui/editor_panel/
  __init__.py          ← re-exports public + test-imported names
  tile_drag.py         ← TILE_DRAG_MIME, _decode_tile_drag_payload,
                         _compute_insertion_index, _filter_selection_by_zone,
                         _apply_tile_drop              (~120 lines)
  flow_layout.py       ← _flow_position,
                         _flow_position_with_gaps       (~50 lines)
  sort.py              ← _sort_group_items              (~15 lines)
  pixmap_loader.py     ← PixmapLoader (QThread)         (~35 lines)
  tile_widgets.py      ← _ColorLine, ClickableLabel,
                         _PinPlaceholderRow,
                         _PinPlaceholderTile            (~280 lines)
  panel.py             ← EditorPanel                    (~1290 lines)
```

Groupings reflect actual cohesion:

- **`tile_drag.py`** — pure-Python drag math. `tests/test_tile_drag.py` already tests these
  helpers together, so the grouping mirrors the existing test boundary.
- **`sort.py`** — isolated because `tests/test_pinned_sort.py` imports `_sort_group_items`
  standalone. Tiny module, cheap to keep separate.
- **`flow_layout.py`** — pure geometry shared by grid rebuild and reflow paths.
- **`pixmap_loader.py`** — a `QThread` subclass with distinct lifecycle concerns.
- **`tile_widgets.py`** — `QLabel` subclasses used as tiles and drop placeholders. Share
  drag-source/target behavior patterns.
- **`panel.py`** — `EditorPanel` stays whole. This is the scope boundary of Option A.

## Re-export strategy

`ui/editor_panel/__init__.py`:

```python
"""EditorPanel package — split for maintainability.

Public surface preserved from pre-split ui/editor_panel.py.
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
```

**External imports that must keep working:**

- `from ui.editor_panel import EditorPanel` → `ui/image_editor_window.py`, `tests/test_editor_panel.py`
- `from ui.editor_panel import _sort_group_items` → `tests/test_pinned_sort.py`
- `from ui.editor_panel import _compute_insertion_index, _filter_selection_by_zone, _apply_tile_drop` → `tests/test_tile_drag.py`

All satisfied by `__init__.py`.

**Internal imports** (inside the package) go direct to the sibling module, not through
`ui.editor_panel`, to avoid init-time re-export loops. For example, `panel.py` writes:

```python
from ui.editor_panel.tile_drag import TILE_DRAG_MIME, _apply_tile_drop, ...
from ui.editor_panel.flow_layout import _flow_position, _flow_position_with_gaps
from ui.editor_panel.sort import _sort_group_items
from ui.editor_panel.pixmap_loader import PixmapLoader
from ui.editor_panel.tile_widgets import ClickableLabel, _PinPlaceholderRow, ...
```

## Migration steps

Branch: `chore/split-editor-panel` off `main`. Each numbered step is a commit with tests
run before commit. If any step breaks, revert that step only — prior steps remain good.

1. **Create package skeleton.** `mkdir ui/editor_panel/`. `git mv ui/editor_panel.py ui/editor_panel/__init__.py`. Preserves blame. File content unchanged — nothing broken yet. Run tests.
2. **Extract `sort.py`.** Move `_sort_group_items` into new file. Add re-export to `__init__.py`. Tests.
3. **Extract `flow_layout.py`.** Move `_flow_position`, `_flow_position_with_gaps`. Re-export. Tests.
4. **Extract `tile_drag.py`.** Move `TILE_DRAG_MIME` and the four drag helpers. Re-export. Tests.
5. **Extract `pixmap_loader.py`.** Move `PixmapLoader`. Re-export. Tests.
6. **Extract `tile_widgets.py`.** Move `_ColorLine`, `ClickableLabel`, `_PinPlaceholderRow`, `_PinPlaceholderTile`. Re-export. Tests. *Circular-import watch* — `ClickableLabel._find_editor` walks `self.parent()` at runtime, no static `EditorPanel` import; should be safe.
7. **Move `EditorPanel` → `panel.py`.** The remaining class moves out of `__init__.py` into `panel.py`. `__init__.py` becomes the pure re-export file above. Tests.
8. **Full smoke test.** `python main.py`, manual run-through (see Verification).

Order reasoning: pure helpers first (lowest risk, tested), widget classes before `panel.py`
so its imports resolve, `EditorPanel` last with an isolated blast radius.

## Verification

**After each extraction step:**

1. `python -m pytest tests/ -q` — all tests pass.
2. Import smoke:
   ```
   python -c "from ui.editor_panel import EditorPanel, _sort_group_items, \
   _compute_insertion_index, _filter_selection_by_zone, _apply_tile_drop, \
   TILE_DRAG_MIME, ClickableLabel, PixmapLoader, _PinPlaceholderRow, \
   _PinPlaceholderTile; print('OK')"
   ```
3. `python main.py` launches — catches import-time errors the unit tests miss.

**Final manual smoke test (step 8):**

- Open editor window in both detached and docked (via settings) modes.
- Add files via button and via OS drag-drop.
- Add folder.
- List view: click tiles, shift-click range, ctrl-click multi-select, delete selected.
- Grid view: same selection actions plus zoom slider, context menu, pin/unpin, set timer.
- Drag tile from list → pinned zone, pinned → list, multi-select drag.
- Toggle class mode: selection and context menu must be disabled (per prior spec).
- Clear all, close app, relaunch — state persists.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Circular import `tile_widgets.py` ↔ `panel.py` | `ClickableLabel._find_editor` uses runtime `self.parent()` walk; no static import of `EditorPanel`. Verified during step 6. |
| Hidden file-private usage (e.g. a module-level constant referenced only inside a method) | Grep each extracted symbol before moving; check for stale references after the move. |
| Qt test collection conflicts (shared `QApplication` singleton) | If tests flake after a step, retry with `pytest --forked` before suspecting the split. |
| `git mv` not detected as rename | Use `git mv` explicitly per file. Verify with `git log --follow` after each step. |

## Success criteria

- All existing tests pass.
- `python main.py` launches and the editor is fully usable per the smoke checklist.
- `wc -l ui/editor_panel/*.py` shows no single file above ~1300 lines, and the sum ≈ prior 1787.
- `git log --follow` on each extracted symbol shows continuous history.
- Oksana runs the app and approves before the PR is merged.

## Deferred — Option B (follow-up PR, out of scope here)

After Option A lands, `panel.py` still holds ~1290 lines. If it still feels unwieldy — or if
Bundle B items 2-5 surface cleaner seams — consider carving `EditorPanel` further. Candidate
seams:

- **`controllers/drag_drop.py`** — `_start_tile_drag`, `_apply_source_ghost_opacity`, `_handle_tile_drop`, `_handle_external_drop`, `_drag_enter`, `_drag_move`, `_drop_event`, `_install_list_drop_handler`. ~250 lines.
- **`controllers/selection.py`** — `_on_tile_click`, `_select_tile`, `_deselect_tile`, `_clear_selection`, `_get_all_tile_labels`. ~80 lines.
- **`views/list_view.py`** — `_rebuild_list` and list-specific context menu. ~150 lines.
- **`views/grid_view.py`** — `_rebuild_grid`, `_reflow_grid`, `_relayout_grid_with_gap`, `_compute_tile_rects`, `_on_zoom`. ~200 lines.
- **`pixmap_cache.py`** — `_get_pixmap`, `_tile_pixmap`, `_on_pixmap_loaded`. ~60 lines. Ties naturally to Bundle B item 3 (LRU cap).

Shape to be decided in a separate brainstorm: helper classes holding a back-reference to
`EditorPanel`, or free functions taking explicit state arguments. Extraction is non-trivial
because these methods read and mutate shared `EditorPanel` state (`self.images`, `self.theme`,
selection state, signals, viewport refs).

**Do not start Option B during this branch.** It lands only if and when motivated by
Bundle B items 2-5 requiring cleaner seams.
