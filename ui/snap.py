# ui/snap.py
"""Winamp-style magnetic snap between frameless windows."""
from PyQt6.QtCore import Qt, QPoint


SNAP_DISTANCE = 15

# Global registry of all snap-capable windows
_snap_windows = []


class SnapMixin:
    """Mixin for QWidget that adds magnetic snap behavior.

    Add to a frameless QWidget class via multiple inheritance:
        class MyWindow(QWidget, SnapMixin):
            def __init__(self):
                QWidget.__init__(self)
                SnapMixin.__init__(self)
    """

    def snap_init(self):
        """Call this in __init__ after QWidget.__init__."""
        self._drag_pos = None
        self._snapped_to = None  # (other_window, side)
        self._snapped_children = []  # [(window, side), ...]
        _snap_windows.append(self)

    def snap_cleanup(self):
        """Call this in closeEvent."""
        if self in _snap_windows:
            _snap_windows.remove(self)
        # Detach from parent
        if self._snapped_to is not None:
            other, _ = self._snapped_to
            other._snapped_children = [
                (w, s) for w, s in other._snapped_children if w is not self]
            self._snapped_to = None
        # Detach children
        for child, _ in list(self._snapped_children):
            child._snapped_to = None
        self._snapped_children.clear()

    def snap_mouse_press(self, event):
        """Call from mousePressEvent."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            return True
        return False

    def snap_mouse_move(self, event):
        """Call from mouseMoveEvent. Returns True if handled."""
        if not (event.buttons() & Qt.MouseButton.LeftButton) or self._drag_pos is None:
            return False

        new_pos = event.globalPosition().toPoint() - self._drag_pos

        # If snapped, check if dragged far enough to detach
        if self._snapped_to is not None:
            other, side = self._snapped_to
            snapped_pos = self._calc_snap_pos(other, side)
            if snapped_pos is not None:
                delta = new_pos - snapped_pos
                if abs(delta.x()) > SNAP_DISTANCE * 2 or abs(delta.y()) > SNAP_DISTANCE * 2:
                    # Detach
                    other._snapped_children = [
                        (w, s) for w, s in other._snapped_children if w is not self]
                    self._snapped_to = None
                else:
                    event.accept()
                    return True

        # Try snap to another window
        best_snap = None
        best_dist = SNAP_DISTANCE

        for other in _snap_windows:
            if other is self or not other.isVisible():
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
            if self._snapped_to is None or self._snapped_to[0] is not other:
                if self._snapped_to is not None:
                    old_other, _ = self._snapped_to
                    old_other._snapped_children = [
                        (w, s) for w, s in old_other._snapped_children if w is not self]
                self._snapped_to = (other, side)
                other._snapped_children.append((self, side))
        else:
            self.move(new_pos)

        self._move_children()
        event.accept()
        return True

    def snap_mouse_release(self, event):
        """Call from mouseReleaseEvent."""
        self._drag_pos = None

    def _move_children(self):
        for child, side in self._snapped_children:
            snap_pos = child._calc_snap_pos(self, side)
            if snap_pos is not None:
                child.move(snap_pos)
                child._move_children()

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
        sd = SNAP_DISTANCE

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
