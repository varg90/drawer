"""Focus-aware pause: toggle + cycling app selector widget."""

import qtawesome as qta
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QLabel, QPushButton,
                              QMenu)
from PyQt6.QtCore import Qt, pyqtSignal
from ui.icons import Icons
from ui.scales import S
from ui.widgets import IconButton
from core.focus_monitor import list_window_apps

NUM_SLOTS = 5


class FocusTrackerState:
    """Pure logic for focus tracker — no Qt dependency, easy to test."""

    def __init__(self, saved_apps=None, enabled=False, slot_index=0):
        self.enabled = enabled
        self.slot_index = slot_index
        if saved_apps is None:
            self.saved_apps = [None] * NUM_SLOTS
        else:
            self.saved_apps = list(saved_apps)

    @property
    def current_app(self):
        return self.saved_apps[self.slot_index]

    def set_app(self, slot, name):
        self.saved_apps[slot] = name

    def clear_slot(self, slot):
        self.saved_apps[slot] = None

    def next_slot(self):
        self.slot_index = (self.slot_index + 1) % NUM_SLOTS

    def prev_slot(self):
        self.slot_index = (self.slot_index - 1) % NUM_SLOTS

    def save_state(self):
        return {
            "focus_enabled": self.enabled,
            "focus_slot": self.slot_index,
            "focus_apps": list(self.saved_apps),
        }

    def restore_state(self, data):
        self.enabled = data.get("focus_enabled", False)
        self.slot_index = data.get("focus_slot", 0)
        apps = data.get("focus_apps", [None] * NUM_SLOTS)
        # Normalize to exactly NUM_SLOTS entries
        apps = list(apps[:NUM_SLOTS])
        while len(apps) < NUM_SLOTS:
            apps.append(None)
        self.saved_apps = apps
        self.slot_index = min(self.slot_index, NUM_SLOTS - 1)


class FocusTrackerWidget(QWidget):
    """Toggle + cycling app-selector for focus-aware pause."""

    tracking_changed = pyqtSignal(bool, str)  # (enabled, app_name_or_empty)

    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._state = FocusTrackerState()

        self._build()

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(0, 0, 0, 0)

        # Toggle button (icon style)
        self._toggle_btn = IconButton(size=S.ICON_HEADER)
        self._toggle_btn.clicked.connect(self._on_toggle)
        layout.addWidget(self._toggle_btn)

        # Label
        self._label = QLabel("Pause with app")
        self._label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._label)

        # App selector button (cycles on click)
        self._app_btn = QPushButton("Select")
        self._app_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._app_btn.clicked.connect(self._on_next)
        self._app_btn.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu)
        self._app_btn.customContextMenuRequested.connect(self._on_prev)
        self._app_btn.hide()
        layout.addWidget(self._app_btn)

        # Action button: arrow (open list) or x (clear slot)
        self._action_btn = IconButton(size=S.FONT_FOCUS_BTN)
        self._action_btn.clicked.connect(self._on_action)
        self._action_btn.hide()
        layout.addWidget(self._action_btn)

        layout.addStretch()
        self._update_display()

    def _on_toggle(self):
        self._state.enabled = not self._state.enabled
        self._update_display()
        self._emit()

    def _on_next(self):
        self._state.next_slot()
        self._update_display()
        self._emit()

    def _on_prev(self, pos=None):
        self._state.prev_slot()
        self._update_display()
        self._emit()

    def _on_action(self):
        if self._state.current_app:
            # Clear current slot
            self._state.clear_slot(self._state.slot_index)
            self._update_display()
            self._emit()
        else:
            # Show running apps dropdown
            self._show_app_list()

    def _show_app_list(self):
        apps = list_window_apps()
        if not apps:
            return
        menu = QMenu(self)
        t = self.theme
        menu.setStyleSheet(
            f"QMenu {{ background: {t.bg}; color: {t.text_primary}; "
            f"border: 1px solid {t.border}; font-family: 'Lexend'; "
            f"font-size: {S.FONT_FOCUS_BTN}px; "
            f"max-height: {S.FOCUS_DROPDOWN_MAX * 24}px; }}"
            f"QMenu::item {{ padding: 4px 12px; }}"
            f"QMenu::item:selected {{ background: {t.bg_active}; }}")
        for app_name in apps:
            action = menu.addAction(app_name)
            action.triggered.connect(
                lambda checked, n=app_name: self._pick_app(n))
        menu.exec(self._action_btn.mapToGlobal(
            self._action_btn.rect().bottomLeft()))

    def _pick_app(self, name):
        self._state.set_app(self._state.slot_index, name)
        self._update_display()
        self._emit()

    def _update_display(self):
        t = self.theme
        enabled = self._state.enabled

        # Toggle icon
        icon_name = Icons.FOCUS_ON if enabled else Icons.FOCUS_OFF
        icon_color = t.text_secondary if enabled else t.text_hint
        self._toggle_btn.setIcon(qta.icon(icon_name, color=icon_color))

        self._label.setStyleSheet(
            f"color: {t.text_hint}; font-size: {S.FONT_FOCUS_BTN}px; "
            f"font-family: 'Lexend'; font-weight: 400;")

        if not enabled:
            self._label.setText("Pause with app")
            self._app_btn.hide()
            self._action_btn.hide()
            return

        self._label.setText("Pause with:")

        current = self._state.current_app
        if current:
            self._app_btn.setText(current)
            self._app_btn.setStyleSheet(
                f"color: {t.accent}; font-size: {S.FONT_FOCUS_BTN}px; "
                f"font-weight: 500; font-family: 'Lexend'; "
                f"background: transparent; border: none; padding: 0; "
                f"text-decoration: underline;")
            # Show X to clear
            self._action_btn.setIcon(
                qta.icon(Icons.CLOSE, color=t.text_hint))
        else:
            self._app_btn.setText("Select")
            self._app_btn.setStyleSheet(
                f"color: {t.text_hint}; font-size: {S.FONT_FOCUS_BTN}px; "
                f"font-weight: 400; font-family: 'Lexend'; "
                f"background: transparent; border: none; padding: 0;")
            # Show arrow to pick
            self._action_btn.setIcon(
                qta.icon(Icons.CARET_DOWN, color=t.text_hint))

        self._app_btn.show()
        self._action_btn.show()

    def _emit(self):
        app = self._state.current_app or ""
        self.tracking_changed.emit(self._state.enabled, app)

    # ---- Public API for save/restore ----

    def save_state(self):
        return self._state.save_state()

    def restore_state(self, data):
        self._state.restore_state(data)
        self._update_display()

    def apply_theme(self):
        self._update_display()

    @property
    def is_tracking(self):
        """True if enabled and an app is selected."""
        return self._state.enabled and self._state.current_app is not None

    @property
    def tracked_app(self):
        """Name of the app being tracked, or None."""
        return self._state.current_app if self._state.enabled else None
