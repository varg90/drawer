# ui/editor_panel/flow_layout.py
"""Flow-layout geometry helpers for the editor grid view."""


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


def _flow_position_with_gaps(labels_or_none, container_width, sz, gap=1):
    """Same as _flow_position but accepts None entries which reserve a
    tile-sized empty slot at that position (no widget moved)."""
    x, y, row_h = 0, 0, 0
    for entry in labels_or_none:
        if entry is None:
            w, h = sz, sz
        else:
            pix = entry.pixmap()
            if pix and not pix.isNull():
                w, h = pix.width(), pix.height()
            else:
                w, h = sz, sz
        if x + w > container_width and x > 0:
            x = 0
            y += row_h + gap
            row_h = 0
        if entry is not None:
            entry.setFixedSize(w, h)
            entry.move(x, y)
        x += w + gap
        row_h = max(row_h, h)
    return y + row_h if labels_or_none else 0
