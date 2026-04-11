"""TimerPanel — mode tabs + timer button grid (quick presets & class tiers)."""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal
from core.constants import TIMER_PRESETS
from core.class_mode import auto_distribute, groups_to_timers, total_duration
from core.timer_logic import format_time
from ui.scales import S
from ui.widgets import make_timer_btn, timer_btn_style

ALL_TIERS = [(30, "30s"), (60, "1m"), (180, "3m"),
             (300, "5m"), (600, "10m"), (900, "15m"),
             (1800, "30m"), (3600, "1h")]


class TimerPanel(QWidget):
    """Mode tabs + 2x4 timer button grid. Owns preset/tier state."""

    # Emitted when timer config changes (mode switch, preset click, tier toggle).
    # Listeners should call get_timer_seconds() / get_class_groups() for details.
    timer_config_changed = pyqtSignal()

    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._timer_mode = "quick"
        self._preset_index = 3  # default 5min
        self._class_groups = []

        self._build()

    # ------------------------------------------------------------------ Build

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Mode row
        mode_row = QHBoxLayout()
        mode_row.setSpacing(0)
        mode_row.setContentsMargins(0, 0, 0, 0)

        self._class_btn = QPushButton("class", self)
        self._class_btn.setFixedHeight(28)
        self._class_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._class_btn.clicked.connect(lambda: self.set_timer_mode("class"))

        self._quick_btn = QPushButton("quick", self)
        self._quick_btn.setFixedHeight(28)
        self._quick_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._quick_btn.clicked.connect(lambda: self.set_timer_mode("quick"))

        mode_row.addWidget(self._class_btn, 1)
        mode_row.addSpacing(4)
        mode_row.addWidget(self._quick_btn, 1)
        layout.addLayout(mode_row)
        layout.addSpacing(S.SPACING_MODE)

        # Timer buttons (2 rows x 4)
        self._quick_btns = []
        self._class_btns = []

        timer_grid = QVBoxLayout()
        timer_grid.setSpacing(S.SPACING_TIERS)
        timer_grid.setContentsMargins(0, 0, 0, 0)

        for row_idx in range(2):
            row_layout = QHBoxLayout()
            row_layout.setSpacing(S.SPACING_TIERS)
            row_layout.setContentsMargins(0, 0, 0, 0)
            for col_idx in range(4):
                global_idx = row_idx * 4 + col_idx
                q_secs, q_label = TIMER_PRESETS[global_idx]
                c_secs, c_label = ALL_TIERS[global_idx]

                q_active = (global_idx == self._preset_index)
                q_btn = make_timer_btn(q_label, q_active, self.theme, parent=self)
                q_btn.clicked.connect(lambda checked, s=q_secs: self._select_preset(s))

                c_btn = make_timer_btn(c_label, False, self.theme, parent=self)
                c_btn.setCheckable(True)
                c_btn.clicked.connect(lambda checked, s=c_secs: self._on_tier_clicked(s))

                self._quick_btns.append((q_btn, q_secs))
                self._class_btns.append((c_btn, c_secs))

                cell = QWidget(self)
                cell_layout = QHBoxLayout(cell)
                cell_layout.setContentsMargins(0, 0, 0, 0)
                cell_layout.addWidget(q_btn)
                cell_layout.addWidget(c_btn)
                c_btn.hide()

                row_layout.addWidget(cell)
            timer_grid.addLayout(row_layout)

        layout.addLayout(timer_grid)

    # ------------------------------------------------------------------ Mode

    def set_timer_mode(self, mode):
        self._timer_mode = mode
        if mode == "quick":
            for btn, _ in self._quick_btns:
                btn.show()
            for btn, _ in self._class_btns:
                btn.hide()
        else:
            for btn, _ in self._quick_btns:
                btn.hide()
            for btn, _ in self._class_btns:
                btn.show()
        self._update_mode_styles()
        self.timer_config_changed.emit()

    @property
    def timer_mode(self):
        return self._timer_mode

    def _update_mode_styles(self):
        t = self.theme
        active_s = (
            f"background-color: {t.start_bg}; color: {t.bg_panel}; "
            f"font-family: 'Lexend'; font-size: {S.FONT_MODE}px; font-weight: 500; "
            f"border-radius: {S.MODE_BTN_RADIUS}px; border: none; "
            f"padding: 4px 8px;")
        inactive_s = (
            f"background-color: {t.bg_button}; color: {t.text_secondary}; "
            f"font-family: 'Lexend'; font-size: {S.FONT_MODE}px; font-weight: 500; "
            f"border-radius: {S.MODE_BTN_RADIUS}px; border: none; "
            f"padding: 4px 8px;")
        if self._timer_mode == "class":
            self._class_btn.setStyleSheet(active_s)
            self._quick_btn.setStyleSheet(inactive_s)
        else:
            self._class_btn.setStyleSheet(inactive_s)
            self._quick_btn.setStyleSheet(active_s)

    # ------------------------------------------------------------------ Quick presets

    def _select_preset(self, secs):
        for i, (s, _) in enumerate(TIMER_PRESETS):
            if s == secs:
                self._preset_index = i
                self._update_preset_styles()
                self.timer_config_changed.emit()
                return

    def _update_preset_styles(self):
        t = self.theme
        current_secs = TIMER_PRESETS[self._preset_index][0]
        for btn, secs in self._quick_btns:
            btn.setStyleSheet(timer_btn_style(secs == current_secs, t))

    def get_timer_seconds(self):
        return TIMER_PRESETS[self._preset_index][0]

    @property
    def preset_index(self):
        return self._preset_index

    @preset_index.setter
    def preset_index(self, value):
        self._preset_index = min(value, len(TIMER_PRESETS) - 1)

    # ------------------------------------------------------------------ Class tiers

    def _on_tier_clicked(self, secs):
        for btn, s in self._class_btns:
            if s == secs:
                break
        self._update_tier_styles()
        self.timer_config_changed.emit()

    def get_selected_tiers(self):
        tiers = []
        for btn, secs in self._class_btns:
            if btn.isChecked():
                for s, label in ALL_TIERS:
                    if s == secs:
                        tiers.append((secs, label))
                        break
        return tiers if tiers else None

    def _update_tier_styles(self):
        t = self.theme
        for btn, secs in self._class_btns:
            btn.setStyleSheet(timer_btn_style(btn.isChecked(), t))

    # ------------------------------------------------------------------ Auto-distribute

    def auto_distribute(self, image_count):
        """Run auto-distribute for class mode. Returns groups list."""
        if not image_count:
            self._class_groups = []
            return
        self._class_groups = auto_distribute(
            image_count, custom_tiers=self.get_selected_tiers())

    @property
    def class_groups(self):
        return self._class_groups

    @class_groups.setter
    def class_groups(self, value):
        self._class_groups = value

    # ------------------------------------------------------------------ Theme

    def apply_theme(self):
        self._update_mode_styles()
        self._update_preset_styles()
        self._update_tier_styles()

    # ------------------------------------------------------------------ Session save/restore

    def save_state(self):
        return {
            "timer_mode": "class" if self._timer_mode == "class" else "standard",
            "timer_seconds": self.get_timer_seconds(),
            "tiers": [secs for btn, secs in self._class_btns if btn.isChecked()],
        }

    def restore_state(self, data):
        timer_secs = data.get("timer_seconds", 300)
        for i, (s, _) in enumerate(TIMER_PRESETS):
            if s == timer_secs:
                self._preset_index = i
                break
        self._preset_index = min(self._preset_index, len(TIMER_PRESETS) - 1)

        _MODE_MAP = {"standard": "quick", "session": "class", "class": "class"}
        self._timer_mode = _MODE_MAP.get(data.get("timer_mode", "quick"), "quick")

        saved_tiers = data.get("tiers")
        if saved_tiers is not None:
            for btn, secs in self._class_btns:
                btn.setChecked(secs in saved_tiers)
            self._update_tier_styles()

        self._update_preset_styles()
        self.set_timer_mode(self._timer_mode)
