# ui/snap.py
"""Winamp-style magnetic snap between frameless windows."""
import weakref
from PyQt6.QtCore import Qt, QPoint
from ui.scales import S

# Global registry of all snap-capable windows (weak refs — auto-cleaned)
_snap_windows = []


def _live_windows():
    """Return alive windows, pruning dead refs."""
    global _snap_windows
    alive = [(ref, ref()) for ref in _snap_windows]
    _snap_windows[:] = [ref for ref, obj in alive if obj is not None]
    return [obj for _, obj in alive if obj is not None]


class SnapMixin:
    """Mixin for QWidget that adds magnetic snap behavior."""

    def __init__(self):
        self.snap_init()

    def snap_init(self):
        self._drag_pos = None
        self._snapped_to = None  # (weakref, side)
        self._snapped_children = []  # [(weakref, side), ...]
        if not any(ref() is self for ref in _snap_windows):
            _snap_windows.append(weakref.ref(self))

    def snap_cleanup(self):
        global _snap_windows
        _snap_windows[:] = [ref for ref in _snap_windows if ref() is not None and ref() is not self]
        if self._snapped_to is not None:
            other_ref, _ = self._snapped_to
            other = other_ref()
            if other is not None:
                other._snapped_children = [
                    (wr, s) for wr, s in other._snapped_children
                    if wr() is not None and wr() is not self]
            self._snapped_to = None
        for child_ref, _ in list(self._snapped_children):
            child = child_ref()
            if child is not None:
                child._snapped_to = None
        self._snapped_children.clear()

    def snap_mouse_press(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            return True
        return False

    def snap_mouse_move(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton) or self._drag_pos is None:
            return False

        new_pos = event.globalPosition().toPoint() - self._drag_pos

        # If we have children snapped to us — just move, no snap detection
        if self._snapped_children:
            self.move(new_pos)
            self._move_children()
            event.accept()
            return True

        # If snapped to another window, check detach threshold
        if self._snapped_to is not None:
            other_ref, side = self._snapped_to
            other = other_ref()
            if other is None:
                self._snapped_to = None
            else:
                snapped_pos = self._calc_snap_pos(other, side)
                if snapped_pos is not None:
                    delta = new_pos - snapped_pos
                    if abs(delta.x()) > S.DETACH_DISTANCE or abs(delta.y()) > S.DETACH_DISTANCE:
                        other._snapped_children = [
                            (wr, s) for wr, s in other._snapped_children
                            if wr() is not None and wr() is not self]
                        self._snapped_to = None
                        self.move(new_pos)
                        self.update()
                        other.update()
                        event.accept()
                        return True
                    else:
                        event.accept()
                        return True

        # Free window — try snap to another
        best_snap = None
        best_dist = S.SNAP_DISTANCE

        for other in _live_windows():
            if other is self or not other.isVisible():
                continue
            # Skip windows already snapped to us
            if any(wr() is other for wr, _ in self._snapped_children):
                continue
            snap = self._find_snap(new_pos, other)
            if snap is not None:
                side, dist, snap_pos = snap
                if dist < best_dist:
                    best_dist = dist
                    best_snap = (other, side, snap_pos)

        if best_snap is not None:
            other, side, snap_pos = best_snap
            self.move(snap_pos)
            self._snapped_to = (weakref.ref(other), side)
            if not any(wr() is self for wr, _ in other._snapped_children):
                other._snapped_children.append((weakref.ref(self), side))
            self.update()
            other.update()
        else:
            self.move(new_pos)

        event.accept()
        return True

    def snap_mouse_release(self, event):
        self._drag_pos = None

    def _move_children(self, _visited=None):
        if _visited is None:
            _visited = set()
        _visited.add(id(self))
        for child_ref, side in self._snapped_children:
            child = child_ref()
            if child is None or id(child) in _visited:
                continue
            snap_pos = child._calc_snap_pos(self, side)
            if snap_pos is not None:
                child.move(snap_pos)
                child._move_children(_visited)

    def _calc_snap_pos(self, other, side):
        og = other.geometry()
        if side == "right":
            return QPoint(og.right() + 1, og.top())
        elif side == "left":
            return QPoint(og.left() - self.width(), og.top())
        elif side == "bottom":
            return QPoint(og.left(), og.bottom() + 1)
        elif side == "top":
            return QPoint(og.left(), og.top() - self.height())
        return None

    def _find_snap(self, my_pos, other):
        og = other.geometry()
        my_w, my_h = self.width(), self.height()
        candidates = []
        sd = S.SNAP_DISTANCE

        # Right of other
        rx = og.right() + 1
        dy = my_pos.y() - og.top()
        if abs(my_pos.x() - rx) < sd and abs(dy) < og.height() + sd:
            sy = og.top() if abs(dy) < sd else my_pos.y()
            candidates.append(("right", abs(my_pos.x() - rx), QPoint(rx, sy)))

        # Left of other
        lx = og.left() - my_w
        if abs(my_pos.x() - lx) < sd and abs(dy) < og.height() + sd:
            sy = og.top() if abs(dy) < sd else my_pos.y()
            candidates.append(("left", abs(my_pos.x() - lx), QPoint(lx, sy)))

        # Bottom of other
        by = og.bottom() + 1
        dx = my_pos.x() - og.left()
        if abs(my_pos.y() - by) < sd and abs(dx) < og.width() + sd:
            sx = og.left() if abs(dx) < sd else my_pos.x()
            candidates.append(("bottom", abs(my_pos.y() - by), QPoint(sx, by)))

        # Top of other
        ty = og.top() - my_h
        if abs(my_pos.y() - ty) < sd and abs(dx) < og.width() + sd:
            sx = og.left() if abs(dx) < sd else my_pos.x()
            candidates.append(("top", abs(my_pos.y() - ty), QPoint(sx, ty)))

        return min(candidates, key=lambda c: c[1]) if candidates else None
