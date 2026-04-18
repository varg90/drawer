# Tile drag-drop with zone-based pin control — Design

**Date:** 2026-04-18
**Status:** Approved (pending user spec review)
**Scope:** Add drag-drop to the quick-mode editor for reordering and pinning/unpinning. Class mode loses drag entirely. Plus fixes for: selection not clearing on empty-area click, selection-frame corners not matching tile corners, and the tile-view pin icon being too muted/too small.

## Problem

After spec #3 shipped, several related gaps remain:

1. **No bulk pin/unpin.** Pinning 15 images takes 15 right-click → Pin interactions.
2. **Tile view has no drag-drop at all** — reordering requires switching to list view.
3. **Class mode still has `InternalMove`** on list widgets, which contradicts spec #3's "no manual control in class mode" principle.
4. **Selection doesn't clear on empty-area click** — pre-existing bug.
5. **Tile-view selection frame has square corners** while tiles have rounded corners (cosmetic mismatch).
6. **Tile-view pin icon is too subtle.** Uses muted `t.text_hint` color while list-view pinned entries use `t.accent`. Also capped at 20px so the icon stops scaling at larger zoom levels. Flagged in prior sessions as "pin indicator too subtle."

## Decision

**Drag-drop is a quick-mode feature.** Class mode is non-editable in terms of ordering, matching spec #3's direction. In quick mode, tiles can be dragged to reorder; dragging across the pinned↔non-pinned zone boundary flips the tile's pin state in addition to moving it. This doubles as a bulk pin/unpin gesture: select N tiles, drag them across the zone boundary, all N flip.

### Zones

- **Pinned zone:** top of the list. All `img.pinned == True` tiles.
- **Non-pinned zone:** everything else.
- Zone is implicit — position in `self.images` is canonical. Pinned tiles are always contiguous at the head (already guaranteed by quick-mode play-order from spec #1).

### Drag semantics

- Drag within a zone → reorder within that zone.
- Drag across zones → pin state changes to match the target zone, plus reorder.
- Multi-select drag: only tiles in the *pressed tile's zone* move. Other-zone selection members stay put (silently filtered).
- Source tile(s) ghost at ~35% opacity during active drag.
- A tile-sized static gap opens at the insertion point (tiles part to make room). No explicit drop-indicator line.
- A floating tile-ghost follows the cursor; its pin icon appears when the cursor is over the pinned zone and disappears when over the non-pinned zone — live preview of the future pin state.

### Empty-zone affordance

- When no pinned images exist, a **dashed-outline "pin here" placeholder** occupies the first slot — as a tile in tile view, as a row in list view. Dropping on it pins the dragged tile(s). Disappears as soon as one tile is pinned.
- The non-pinned zone has no equivalent placeholder — it only becomes empty when all tiles are pinned, and in that case dragging any pinned tile past the last pinned position works as the unpin gesture.

### List view

- Quick mode keeps Qt's built-in `InternalMove`. A custom `dropEvent` enforces zone rules and applies cross-zone pin flips.
- Class mode sets drag mode to `NoDragDrop`.

### Cosmetic + bug fixes bundled

- Selection-frame border-radius set to match tile corners.
- Selection clears when clicking empty grid/list area.
- Pin icon color in tile view switched from `t.text_hint` to `t.accent`.
- Pin icon size formula changed from `max(8, min(20, int(sz * 0.18)))` to `max(10, int(sz * 0.22))` — icon now scales visibly with tile zoom, floor retained so it doesn't vanish at small tile sizes.

## Rationale

- **Drag-to-pin direct manipulation.** The zone a tile lands in *is* its pin state. This maps cleanly to "move tiles to where they belong."
- **No divider, no tint, no label on the zone boundary.** Pin icons on tiles signal membership. Decorative boundary markers add noise. Empty-zone affordance comes from the placeholder tile, not from a line.
- **Static gap instead of drop-indicator line.** Shifting tiles to make room is already required for any reasonable feedback. A separate line or dashed frame on top overloads the dashed-frame visual (reserved for the empty pin placeholder).
- **Floating ghost preview with pin-state change.** Clearest signal of what the drop will do. More code than a cursor-icon change, but the preview *is* the future state — unambiguous.
- **Class-mode drag removed.** Consistent with spec #3's "no per-image control in class mode." Reordering tiles in class mode shifts auto-distribute outcomes in positional-walk mode anyway, which is already a known bug (see `project_tier_migration_bug` in memory).

## Out of scope

- **Animated tile reorder** (smooth QPropertyAnimation on tile positions during drag). Deferred polish; see `project_animated_reorder.md`. Current decision: static gap + ghost preview is enough. If it feels clunky during daily use, revisit.
- **Shuffle coupling between modes.** `self.images` is shared, so shuffle in one mode affects the other. See `project_shuffle_coupling.md`. Separate spec.
- **Rubber-band selection** (drag in empty area → rectangle select). Natural follow-up but not in #4.
- **Drag between Drawer windows or to external apps.** Internal drag only.
- **Tier migration bug** (class-mode tiers shift at session start due to positional timer assignment) — separate issue, not addressed here.

## Data model

`self.images` stays the single source of truth. Drag operations mutate:
- **Order** — rearranging positions in the list.
- **`img.pinned`** — set True when a tile lands in the pinned zone, False when in the non-pinned zone.

The invariant "all pinned tiles contiguous at the head of `self.images`" is preserved by every drop (the insertion logic places dragged tiles correctly based on target zone).

External file drops are unchanged — disambiguated from internal drags by MIME type (`application/x-drawer-tile-indices` for internal, `text/uri-list` for external file drops).

## Behavior by mode

### Quick mode, tile view

- **Empty pinned zone:** dashed placeholder with centered pin icon at grid position 0. Non-pinned tiles flow after.
- **Populated:** pinned tiles first (pin icons visible in accent color, scaled with tile size), non-pinned after. No divider, label, or tint.
- **Drag start:** mouse press on tile + move ≥5px → `QDrag` with custom MIME carrying JSON-encoded list of source indices.
- **Multi-select drag:** if pressed tile ∈ current selection, drag carries all selected tiles that share the pressed tile's zone. Other-zone selection filtered out.
- **Drag over:** source tiles ghost to 35% opacity. Tile-sized static gap opens at insertion point (tiles after the gap shift right/down). Floating ghost widget follows cursor, pin icon toggling based on cursor zone.
- **Drop:** dragged tiles inserted at gap position; pin states adjusted to match target zone; `self.images` mutated; grid rebuilt; editor change emitted.
- **External file drop** onto the grid is routed by MIME type to the existing add-images handler.

### Quick mode, list view

- `QListWidget` keeps `InternalMove`.
- **Empty pinned zone:** a dashed, disabled placeholder row is prepended at position 0 — non-selectable, non-draggable, drop-accepting. Centered pin icon with "drop here to pin" label. Dropping onto it pins the dropped items and the placeholder disappears.
- Custom `dropEvent` (subclass or inline override):
  - If drop target is the placeholder row: pin dropped items, insert at index 0, remove placeholder.
  - If cross-zone drop on a real row: apply pin flip + reorder.
  - If within-zone: let Qt's default `InternalMove` run, sync via `_on_reorder`.

### Class mode, both views

- Tile view: no drag infrastructure attached.
- List view: `setDragDropMode(NoDragDrop)`.
- Selection, delete, add still work.
- No context menu (from spec #3).

## Code changes

### `ui/editor_panel.py`

1. **`ClickableLabel`** (tile widget) gains:
   - `mousePressEvent` stores press position.
   - `mouseMoveEvent` starts `QDrag` when movement exceeds 5px threshold. Only in quick mode (guarded by `self._timer_mode == "quick"`).
   - Drag payload: MIME `application/x-drawer-tile-indices` with JSON list of source indices (selection if pressed tile is selected, else just the pressed tile).

2. **Grid container** gains `dragEnterEvent`, `dragMoveEvent`, `dragLeaveEvent`, `dropEvent`:
   - `dragEnterEvent`: accept if internal tile-drag MIME present; ignore otherwise (lets external file drops bubble up to `settings_window`).
   - `dragMoveEvent`: compute insertion index from cursor position; shift tile positions to create gap; update floating ghost's pin icon based on zone under cursor.
   - `dropEvent`: apply `_apply_tile_drop(source_indices, insert_idx, target_zone)`; rebuild grid; emit change.
   - `dragLeaveEvent`: restore layout (close gap), dispose floating ghost.

3. **Helper functions** (module-private, pure-Python, unit-testable):
   - `_compute_insertion_index(grid_pos, tile_rects)` → insertion index.
   - `_filter_selection_by_zone(indices, source_zone, images)` → same-zone subset of indices.
   - `_apply_tile_drop(images, source_indices, insert_idx, target_zone)` → new list with reorder + pin flip applied; preserves the "pinned-contiguous-at-head" invariant.

4. **Floating drag ghost** — a small `QLabel` widget styled like a tile at ~60% scale, created on drag start, repositioned on cursor move during drag, pin icon overlay added/removed based on cursor zone. Disposed on drop/cancel.

5. **Pin placeholder (tile view)** — rendered as the first grid item in quick mode when `pinned_count == 0`. Dashed-outline stylesheet, centered pin icon in accent color. Accepts drops via its own `dropEvent` (drops here → pin).

   **Pin placeholder (list view)** — a `QListWidgetItem` prepended at row 0 when `pinned_count == 0` and mode is quick. Flags limited to `ItemIsDropEnabled`; no selection, no drag. Rendered with a dashed-border styled delegate (or custom paint) and a pin icon + "drop here to pin" label. Marked with a custom `Qt.ItemDataRole.UserRole + 1` sentinel so `dropEvent` and `_on_reorder` recognize and handle it.

6. **`_rebuild_grid` changes:**
   - Count pinned tiles.
   - Insert placeholder as first item when `pinned_count == 0` and mode is quick.
   - Pass drag-enabled flag to tile construction (only attach drag handlers in quick mode).

7. **Pin icon color + scaling fix:**
   - `pin_icon = qta.icon(Icons.TOPMOST_ON, color=t.accent)` (was `t.text_hint`).
   - `pin_sz = max(10, int(sz * 0.22))` (was `max(8, min(20, int(sz * 0.18)))`).

8. **Selection-frame rounded corners** — stylesheet for selected-tile border gains `border-radius` matching the tile's `border-radius` (use existing `S.TILE_BORDER_RADIUS` or equivalent constant; add one if absent).

9. **Selection clear on empty-area click:**
   - Grid container `mousePressEvent`: if hit-test finds no tile, clear `_selected_tiles` and trigger rebuild.
   - List widgets: inside the existing `_list_scroll` drop-event wiring, add a click handler on empty area that clears selection.

10. **List-view drag gate:**
    - In `_rebuild_list`, use `setDragDropMode(DragDropMode.InternalMove)` when `self._timer_mode == "quick"`, else `setDragDropMode(DragDropMode.NoDragDrop)`.

11. **Custom `dropEvent` for quick-mode `QListWidget`** (lightweight subclass or inline override):
    - Determine source rows (Qt-selected indices) and target row.
    - If target row is the placeholder: pin the dropped items, insert at index 0 of `self.images`, remove placeholder from the widget, emit change.
    - Else classify source zone and target zone by pin status at source/target rows.
    - If cross-zone: flip pin state for moved items; apply `self.images` mutation to preserve pinned-contiguous invariant; emit change.
    - If same-zone: let Qt's default `InternalMove` run, then sync `self.images` via `_on_reorder` as today.
    - `_on_reorder` must skip the placeholder row (identified by the sentinel UserRole data) when rebuilding `self.images`.

### No changes needed to

- `core/play_order.py` — quick-mode play order already uses `pinned + unpinned` from spec #1.
- `core/models.py` — `ImageItem.pinned` shape unchanged.
- `ui/settings_window.py` — external file drop handler untouched; MIME disambiguation happens in `editor_panel.py`.

## Edge cases

| Case | Behavior |
|------|----------|
| Drop outside grid | Drag cancels, no change. |
| Cross-zone drop of non-pinned tile into pinned zone | Tile becomes pinned, inserts at drop position. |
| Cross-zone drop of pinned tile into non-pinned zone | Tile becomes unpinned, inserts at drop position. If it was the last pinned tile, placeholder reappears. |
| Mixed-zone multi-select drag | Only tiles in the pressed tile's zone move; other-zone selection members stay. |
| Drop at same position as drag start | No-op, no rebuild. |
| Empty image list | No tiles to drag, no drag initiates. |
| Single image | Drag allowed, drop is always a no-op. |
| All tiles pinned | Non-pinned zone is empty. Dragging a pinned tile past the last pinned position unpins it. |
| All tiles non-pinned | Pinned zone shows placeholder. Drop on placeholder → first pin. |
| External file drop (Explorer → grid) | Routed to existing add-images handler via URL MIME check. |
| Click on empty grid/list area | Selection clears. |
| Click on tile | Toggles selection (Ctrl-click = toggle; Shift-click = range — unchanged). |
| Quick ↔ class mode switch during drag | Not reachable — both are main-thread UI. |
| Drag during session playback | Editor and viewer are separate; not reachable. |
| ESC during drag | Qt default cancel — drag aborts. |
| Zoom in/out during session | Pin icon scales up/down with tile size (no cap). |
| List view in quick mode with zero pinned images | Dashed placeholder row prepended at row 0 with "drop here to pin" label. Accepts drops; disappears on first pin. Same behavior as tile view. |

## Testing plan

**Unit tests** (pure Python, no Qt):
- `tests/test_tile_drag.py` — new file.
  - `_compute_insertion_index` returns expected index for a range of cursor positions over a synthetic grid.
  - `_filter_selection_by_zone` drops cross-zone members correctly.
  - `_apply_tile_drop` preserves the pinned-contiguous invariant across all source/target zone combinations (within-zone, pinned→non-pinned, non-pinned→pinned, mixed selection).

**Manual smoke test** (Oksana, post-implementation):
1. Open editor in quick mode, tile view, with 10+ images (none pinned).
2. Verify dashed pin-placeholder appears as the first tile.
3. Drag a non-pinned tile onto the placeholder. Verify tile becomes pinned (accent pin icon appears), placeholder disappears.
4. Drag another non-pinned tile up past the newly-pinned tile. Verify it becomes pinned and joins the pinned row.
5. Drag a pinned tile to reorder within the pinned zone. Verify pin-play-order changed (start a session — the first image played is now whichever pinned tile is leftmost/topmost in the pinned row).
6. Drag a pinned tile down past the last pinned position into the non-pinned zone. Verify it unpins (pin icon disappears).
7. If you unpinned the last pinned tile in step 6, verify the placeholder reappears.
8. Select 3 tiles (mix of pinned and non-pinned). Drag a non-pinned one. Verify only the non-pinned selection members move; pinned selection members stay.
9. Drag a tile outside the grid and release. Verify drag cancels, no change.
10. Drag files from Windows Explorer onto the grid. Verify new images are added normally.
11. Switch to class mode. Attempt to drag a tile. Verify drag cannot start.
12. Class-mode list view: attempt to drag an item. Verify drag cannot start.
12b. Switch back to quick mode, list view, with zero pinned images. Verify the dashed "drop here to pin" placeholder row appears at the top. Drag an item onto it — verify it becomes pinned and the placeholder disappears.
13. Click empty area of the grid/list. Verify selection clears.
14. Select a tile. Verify selection frame has rounded corners matching the tile.
15. Zoom in the tile view. Verify pin icons scale up visibly (no 20px cap).
16. Verify pin icon color matches list-view pinned-entry accent color.

## Acceptance

- Tile-view drag-drop works in quick mode only.
- Within-zone drag reorders tiles.
- Cross-zone drag flips pin state + reorders.
- Multi-select drag moves only same-zone members of the selection.
- Empty pinned zone shows the dashed placeholder in both tile and list views; first pin removes it; last unpin restores it.
- Class mode has no drag-drop in either view.
- Selection clears on empty-area click.
- Selection frame corners match tile corners.
- Tile-view pin icon uses `t.accent` and scales with tile zoom (`0.22` ratio, floor 10px, no cap).
- External file drops from Explorer continue to work unchanged.
