"""Keep the resize cursor from leaking into child widgets of frameless windows.

Frameless windows in Drawer call ``self.setCursor(Qt.SizeHorCursor)`` when the
mouse is near an edge. Qt's cursor inheritance means any child widget without
its own cursor shows the parent's cursor. When the mouse moves from the edge
into a child, the parent's ``mouseMoveEvent`` stops firing (the child captures
mouse events), so the resize cursor stays stuck on the child body.

Fix: install one global Qt event filter that watches ``QEvent.Enter`` on all
widgets. When the mouse enters any descendant of a registered window, clear
the window's cursor — unless a resize drag is in progress.
"""

import weakref

from PyQt6.QtCore import QCoreApplication, QEvent, QObject
from PyQt6.QtWidgets import QWidget


def _window_is_resizing(w):
    return bool(
        getattr(w, "_resize_edge", None)
        or getattr(w, "_resize_corner", None)
        or getattr(w, "_resizing", False)
    )


class _ResizeCursorGuard(QObject):
    _instance = None
    _windows = weakref.WeakSet()

    @classmethod
    def register(cls, window):
        if cls._instance is None:
            cls._instance = cls()
            QCoreApplication.instance().installEventFilter(cls._instance)
        cls._windows.add(window)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Enter and isinstance(obj, QWidget):
            w = obj.window()
            if w is not None and obj is not w and w in self._windows:
                if not _window_is_resizing(w):
                    if hasattr(w, "_last_edge"):
                        w._last_edge = None
                    w.unsetCursor()
        return False


def install_resize_cursor_guard(window):
    """Register a frameless window with the global resize-cursor guard.

    Call once after the window is constructed. No re-install needed when
    children are added later — the guard is a single app-wide filter.
    """
    _ResizeCursorGuard.register(window)
