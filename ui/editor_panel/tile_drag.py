# ui/editor_panel/tile_drag.py
"""Pure-Python tile-drag helpers: MIME constant + payload + geometry +
selection-zone filter + reorder."""

import json


# Payload for an internal tile drag: JSON-encoded bytes matching
#   {"indices": [int, ...], "source_is_pinned": bool}
# - indices:          positions in EditorPanel.images of the dragged tiles,
#                     already filtered to the pressed tile's zone.
# - source_is_pinned: zone of the pressed tile (convenience hint for the
#                     drop target; can also be re-derived from images[i].pinned).
TILE_DRAG_MIME = "application/x-drawer-tile-indices"


def _decode_tile_drag_payload(mime_data):
    """Robustly decode a TILE_DRAG_MIME payload.

    Returns a list of source indices (ints) or None if the payload is absent,
    malformed JSON, wrong shape, or contains non-int entries.
    """
    if not mime_data.hasFormat(TILE_DRAG_MIME):
        return None
    try:
        raw = bytes(mime_data.data(TILE_DRAG_MIME)).decode("utf-8")
        payload = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    indices = payload.get("indices")
    if not isinstance(indices, list) or not indices:
        return None
    if not all(isinstance(i, int) for i in indices):
        return None
    return indices


def _compute_insertion_index(cursor_pos, tile_rects):
    """Given cursor position (x, y) in the grid container's coordinate system
    and a list of tile rects (idx, x, y, w, h), return the insertion index
    where a dropped tile would land.

    Algorithm:
    - Find the row whose vertical range (y, y+h) contains cursor_y (clamped to
      the nearest row if cursor is above or below all tiles).
    - Within that row, find the first tile whose horizontal midline is past
      cursor_x. Insertion is before that tile.
    - If cursor is after the last tile in the row, insertion is after the
      last tile of the row (which is the index of the first tile in the next
      row, or len(tile_rects) if this is the last row).
    """
    if not tile_rects:
        return 0

    cx, cy = cursor_pos

    # Group rects by row (rects with the same y).
    rows = {}
    for rect in tile_rects:
        idx, x, y, w, h = rect
        rows.setdefault(y, []).append(rect)
    row_ys = sorted(rows.keys())

    # Pick the row the cursor is in (clamp).
    target_y = row_ys[0]
    for y in row_ys:
        h = rows[y][0][4]
        if y <= cy < y + h:
            target_y = y
            break
        if cy >= y:
            target_y = y

    row = sorted(rows[target_y], key=lambda r: r[1])  # sort by x
    for rect in row:
        idx, x, y, w, h = rect
        midline = x + w / 2
        if cx < midline:
            return idx
    # Cursor is past the last tile in this row — insert after it.
    last_idx = row[-1][0]
    return last_idx + 1


def _filter_selection_by_zone(indices, source_is_pinned, images):
    """Return the subset of `indices` whose images share `source_is_pinned`.

    Used when the user presses on a selected tile to start a multi-select
    drag: only tiles in the pressed tile's zone participate."""
    result = []
    for i in indices:
        if 0 <= i < len(images) and bool(images[i].pinned) == source_is_pinned:
            result.append(i)
    return result


def _apply_tile_drop(images, source_indices, insert_idx, target_is_pinned):
    """Return a new images list with source_indices moved to insert_idx and
    their pin state updated to target_is_pinned.

    Mutates img.pinned on moved items in place — the returned list references
    the same ImageItem objects as the input (consistent with _toggle_pin).

    Preserves the 'pinned tiles contiguous at the head' invariant by
    rebuilding the final list as pinned + unpinned. source_indices may span
    the pinned/non-pinned boundary only if the caller already filtered by
    zone.
    """
    # Collect moved items; set their pinned state.
    moved = [images[i] for i in source_indices]
    for img in moved:
        img.pinned = target_is_pinned

    # Remaining = images with moved items removed (preserve order).
    excluded = set(source_indices)
    remaining = [img for i, img in enumerate(images) if i not in excluded]

    # Insertion index is in the space of the ORIGINAL list; translate to the
    # remaining list by subtracting how many source_indices are before it.
    before = sum(1 for i in source_indices if i < insert_idx)
    adj_insert = max(0, insert_idx - before)
    adj_insert = min(adj_insert, len(remaining))

    combined = remaining[:adj_insert] + moved + remaining[adj_insert:]

    # Normalize: pinned contiguous at head.
    pinned = [img for img in combined if img.pinned]
    unpinned = [img for img in combined if not img.pinned]
    return pinned + unpinned
