import os
import qtawesome as qta
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                              QPushButton, QLabel, QFileDialog,
                              QSizePolicy, QApplication, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QColor
from core.constants import SUPPORTED_FORMATS, TIMER_PRESETS, SESSION_PRESETS
from core.timer_logic import format_time
from core.class_mode import auto_distribute, groups_to_timers, total_duration, format_group
from core.file_utils import filter_image_files, scan_folder
from core.session import save_session, load_session
from core.models import ImageItem
from ui.theme import Theme
from ui.scales import S
from ui.icons import Icons
from ui.widgets import (make_icon_btn, make_start_btn, make_icon_toggle,
                         make_centered_header, make_timer_btn)


ALL_TIERS = [(30, "30s"), (60, "1m"), (180, "3m"),
             (300, "5m"), (600, "10m"), (900, "15m"),
             (1800, "30m"), (3600, "1h")]


# DEPRECATED — kept for backward compatibility only
class TierToggle(QPushButton):
    """Deprecated: toggleable tier button. Use make_timer_btn instead."""

    def __init__(self, text, seconds, parent=None):
        super().__init__(text, parent)
        self.seconds = seconds
        self._active = False
        self.setCheckable(True)
        self.setChecked(False)
        self.clicked.connect(self._on_click)

    def _on_click(self):
        self._active = self.isChecked()

    @property
    def active(self):
        return self._active


class SettingsWindow(QMainWindow):
    images_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setWindowTitle("RefBot")
        self.setFixedSize(S.MAIN_W, S.MAIN_H)

        self.images = []
        self.viewer = None
        self.theme = Theme("dark")

        # Dock state for editor panel
        self._dock_mode = "compact"   # "compact", "right", "detached"
        self._editor_panel = None

        # "quick" replaces old "standard", "class" replaces old "session"
        self._timer_mode = "quick"
        self._preset_index = 3   # default 5min
        self._session_index = 5  # default 1h
        self._manual_groups = []
        self._class_groups = []

        # Toggle states (replace checkboxes)
        self._random = False
        self._topmost = False

        self._build_ui()
        self._apply_theme()
        self._restore_session()
        self.setAcceptDrops(True)

    # ------------------------------------------------------------------ UI

    def _build_ui(self):
        # Central widget with horizontal layout for settings + optional docked editor
        central = QWidget()
        self.setCentralWidget(central)
        main_hbox = QHBoxLayout(central)
        main_hbox.setContentsMargins(0, 0, 0, 0)
        main_hbox.setSpacing(0)

        settings_container = QWidget()
        settings_container.setFixedWidth(S.MAIN_W)
        main_hbox.addWidget(settings_container)

        # Vertical divider (hidden until editor docked)
        self._dock_divider = QFrame()
        self._dock_divider.setFrameShape(QFrame.Shape.VLine)
        self._dock_divider.setFixedWidth(1)
        self._dock_divider.hide()
        main_hbox.addWidget(self._dock_divider)

        # Editor container (hidden until editor docked)
        self._editor_container = QWidget()
        self._editor_container.setFixedWidth(S.EDITOR_W)
        self._editor_container.hide()
        main_hbox.addWidget(self._editor_container)

        self.setFixedSize(S.MAIN_W, S.MAIN_H)

        # All settings content goes inside settings_container
        root = QVBoxLayout(settings_container)
        root.setContentsMargins(S.MARGIN, S.MARGIN, S.MARGIN, S.MARGIN_BOTTOM)
        root.setSpacing(0)

        # ── 1. Header ──────────────────────────────────────────────────────
        self._help_btn = make_icon_btn(Icons.INFO, self.theme.text_hint,
                                       size=S.ICON_HEADER, tooltip="Help")
        self._help_btn.clicked.connect(self._show_help)

        self._topmost_btn = make_icon_toggle(
            Icons.TOPMOST_ON, Icons.TOPMOST_OFF, self._topmost, self.theme,
            size=S.ICON_HEADER)
        self._topmost_btn.setToolTip("Always on top")
        self._topmost_btn.clicked.connect(self._toggle_topmost)

        self._accent_btn = QPushButton()
        self._accent_btn.setFixedSize(S.ACCENT_DOT, S.ACCENT_DOT)
        self._accent_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._accent_btn.setToolTip("Accent color")
        self._accent_btn.clicked.connect(self._pick_accent)

        self._theme_btn = make_icon_btn(
            Icons.THEME_DARK if self.theme.name == "dark" else Icons.THEME_LIGHT,
            self.theme.text_hint, size=S.ICON_HEADER)
        self._theme_btn.clicked.connect(self._toggle_theme)

        self._min_btn = make_icon_btn(Icons.MINIMIZE, self.theme.text_hint,
                                      size=S.ICON_HEADER, tooltip="Minimize")
        self._min_btn.clicked.connect(self.showMinimized)

        self._close_btn = make_icon_btn(Icons.CLOSE, self.theme.text_hint,
                                        size=S.ICON_HEADER, tooltip="Close")
        self._close_btn.clicked.connect(self.close)

        header_layout, self._title = make_centered_header(
            "REFBOT",
            [self._help_btn, self._accent_btn, self._theme_btn],
            [self._topmost_btn, self._min_btn, self._close_btn],
            self.theme,
        )
        root.addLayout(header_layout)
        root.addSpacing(S.SPACING_HEADER)

        # ── 2. Mode row + image count ──────────────────────────────────────
        mode_row = QHBoxLayout()
        mode_row.setSpacing(0)
        mode_row.setContentsMargins(0, 0, 0, 0)

        self._class_btn = QPushButton("Class")
        self._class_btn.setFixedHeight(22)
        self._class_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._class_btn.clicked.connect(lambda: self._set_timer_mode("class"))

        self._quick_btn = QPushButton("Quick")
        self._quick_btn.setFixedHeight(22)
        self._quick_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._quick_btn.clicked.connect(lambda: self._set_timer_mode("quick"))

        self._img_count_label = QLabel("0 img")
        self._img_count_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)

        self._add_btn = make_icon_btn(Icons.PLUS, self.theme.text_hint,
                                      size=S.ICON_HEADER, tooltip="Add files")
        self._add_btn.clicked.connect(self._open_editor)

        mode_row.addWidget(self._class_btn)
        mode_row.addWidget(self._quick_btn)
        mode_row.addStretch()
        mode_row.addWidget(self._img_count_label)
        mode_row.addSpacing(4)
        mode_row.addWidget(self._add_btn)
        root.addLayout(mode_row)
        root.addSpacing(S.SPACING_MODE)

        # ── 3. Duration picker ─────────────────────────────────────────────
        dur_row = QHBoxLayout()
        dur_row.setSpacing(0)
        dur_row.setContentsMargins(0, 0, 0, 0)
        dur_row.addStretch()

        self._ses_left = make_icon_btn(Icons.CARET_LEFT, self.theme.text_secondary,
                                       size=S.DURATION_ARROW)
        self._ses_left.setFixedSize(S.DURATION_ARROW_BTN, S.DURATION_ARROW_BTN)
        self._ses_left.clicked.connect(self._prev_session)

        self._ses_display = QLabel("1:00:00")
        self._ses_display.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._ses_right = make_icon_btn(Icons.CARET_RIGHT, self.theme.text_secondary,
                                        size=S.DURATION_ARROW)
        self._ses_right.setFixedSize(S.DURATION_ARROW_BTN, S.DURATION_ARROW_BTN)
        self._ses_right.clicked.connect(self._next_session)

        dur_row.addWidget(self._ses_left)
        dur_row.addWidget(self._ses_display)
        dur_row.addWidget(self._ses_right)
        dur_row.addStretch()
        root.addLayout(dur_row)
        root.addSpacing(S.SPACING_DURATION)

        # ── 4. Timer buttons (2 rows × 4) ──────────────────────────────────
        self._timer_buttons = []  # list of (btn, secs)

        # Quick mode uses TIMER_PRESETS, Class mode uses ALL_TIERS.
        # We build both sets and swap visibility on mode change.
        # Both use identical grid positions — only labels/behavior differ.
        # We build ONE set of 8 buttons per mode and show the right set.

        self._quick_btns = []   # [(btn, secs), ...]
        self._class_btns = []   # [(btn, secs), ...]

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
                q_btn = make_timer_btn(q_label, q_active, self.theme)
                q_btn.clicked.connect(lambda checked, s=q_secs: self._select_preset_by_secs(s))

                c_btn = make_timer_btn(c_label, False, self.theme)
                c_btn.setCheckable(True)
                c_btn.clicked.connect(lambda checked, s=c_secs: self._on_tier_clicked(s))

                self._quick_btns.append((q_btn, q_secs))
                self._class_btns.append((c_btn, c_secs))

                # Stack them in a stacked container widget
                cell = QWidget()
                cell_layout = QHBoxLayout(cell)
                cell_layout.setContentsMargins(0, 0, 0, 0)
                cell_layout.addWidget(q_btn)
                cell_layout.addWidget(c_btn)
                c_btn.hide()  # class buttons hidden by default (quick is default mode)

                row_layout.addWidget(cell)

            timer_grid.addLayout(row_layout)

        root.addLayout(timer_grid)
        root.addSpacing(S.SPACING_SUMMARY)

        # ── 5. Summary line (groups + total) ──────────────────────────────
        self._groups_label = QLabel("")
        self._groups_label.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self._total_label = QLabel("")
        self._total_label.setAlignment(Qt.AlignmentFlag.AlignLeft)

        root.addWidget(self._groups_label)
        root.addWidget(self._total_label)

        # ── 6. Stretch ─────────────────────────────────────────────────────
        root.addStretch()

        # ── 7. Bottom bar: [dice]  ... [start] ────────────────────────────
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(0)
        bottom_row.setContentsMargins(0, 0, 0, 0)

        self._dice_btn = make_icon_toggle(
            Icons.RANDOM_ON, Icons.RANDOM_OFF, self._random, self.theme,
            size=S.ICON_DICE)
        self._dice_btn.setToolTip("Random order")
        self._dice_btn.clicked.connect(self._toggle_random)

        self._start_btn = make_start_btn(self.theme)
        self._start_btn.clicked.connect(self._start_slideshow)

        bottom_row.addWidget(self._dice_btn)
        bottom_row.addStretch()
        bottom_row.addWidget(self._start_btn)

        root.addLayout(bottom_row)

        # ── Initialize display ─────────────────────────────────────────────
        self._update_mode_buttons()
        self._update_preset_styles()
        self._update_session_display()
        self._update_summary()
        self._update_img_count()

    # ------------------------------------------------------------------ Theme

    def _apply_theme(self):
        t = self.theme
        self.setStyleSheet(f"background-color: {t.bg}; color: {t.text_primary};")
        self._dock_divider.setStyleSheet(f"color: {t.border};")

        # Header title (may already exist from make_centered_header, refresh it)
        self._title.setStyleSheet(
            f"color: {t.text_header}; font-size: {S.FONT_TITLE}px; "
            f"font-weight: 500; letter-spacing: 3px;")

        # Header icon buttons
        self._help_btn.setIcon(qta.icon(Icons.INFO, color=t.text_hint))
        self._help_btn.setStyleSheet("background: transparent; border: none; padding: 0px;")

        _topmost_icon = Icons.TOPMOST_ON if self._topmost else Icons.TOPMOST_OFF
        _topmost_color = t.accent if self._topmost else t.text_hint
        self._topmost_btn.setIcon(qta.icon(_topmost_icon, color=_topmost_color))
        self._topmost_btn.setStyleSheet("background: transparent; border: none; padding: 0px;")

        _theme_icon = Icons.THEME_DARK if t.name == "dark" else Icons.THEME_LIGHT
        self._theme_btn.setIcon(qta.icon(_theme_icon, color=t.text_hint))
        self._theme_btn.setStyleSheet("background: transparent; border: none; padding: 0px;")

        self._min_btn.setIcon(qta.icon(Icons.MINIMIZE, color=t.text_hint))
        self._min_btn.setStyleSheet("background: transparent; border: none; padding: 0px;")

        self._close_btn.setIcon(qta.icon(Icons.CLOSE, color=t.text_hint))
        self._close_btn.setStyleSheet("background: transparent; border: none; padding: 0px;")

        self._accent_btn.setStyleSheet(
            f"background-color: {t.accent}; border: 1px solid {t.border}; "
            f"border-radius: {S.ACCENT_DOT // 2}px;")

        # Mode buttons
        self._update_mode_buttons()

        # Image count
        self._img_count_label.setStyleSheet(
            f"color: {t.text_hint}; font-size: {S.FONT_HINT}px; font-weight: 500;")

        self._add_btn.setIcon(qta.icon(Icons.PLUS, color=t.text_hint))
        self._add_btn.setStyleSheet("background: transparent; border: none; padding: 0px;")

        # Duration picker
        _dur_color = t.text_secondary if self._timer_mode == "class" else t.text_hint
        self._ses_left.setIcon(qta.icon(Icons.CARET_LEFT, color=_dur_color))
        self._ses_right.setIcon(qta.icon(Icons.CARET_RIGHT, color=_dur_color))
        self._ses_left.setStyleSheet("background: transparent; border: none; padding: 0px;")
        self._ses_right.setStyleSheet("background: transparent; border: none; padding: 0px;")

        _dur_text = t.text_primary if self._timer_mode == "class" else t.text_hint
        self._ses_display.setStyleSheet(
            f"color: {_dur_text}; font-size: {S.FONT_DURATION}px; font-weight: 400;")

        # Timer buttons
        self._update_preset_styles()
        self._update_tier_styles()

        # Summary
        self._groups_label.setStyleSheet(
            f"color: {t.text_secondary}; font-size: {S.FONT_HINT}px; font-weight: 500;")
        self._total_label.setStyleSheet(
            f"color: {t.text_secondary}; font-size: {S.FONT_TOTAL}px; font-weight: 500;")

        # Bottom bar
        _dice_icon = Icons.RANDOM_ON if self._random else Icons.RANDOM_OFF
        _dice_color = t.accent if self._random else t.text_hint
        self._dice_btn.setIcon(qta.icon(_dice_icon, color=_dice_color))
        self._dice_btn.setStyleSheet("background: transparent; border: none; padding: 0px;")

        # Refresh start button
        self._start_btn.setIcon(qta.icon(Icons.START, color=t.start_text))
        self._start_btn.setStyleSheet(
            f"background-color: {t.start_bg}; border: none; "
            f"border-radius: {int(S.ICON_START * S.START_RADIUS_RATIO)}px;")

    # ------------------------------------------------------------------ Window dragging

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and hasattr(self, '_drag_pos'):
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if hasattr(self, '_drag_pos'):
            del self._drag_pos

    # ------------------------------------------------------------------ Help / Theme / Accent

    def _show_help(self):
        from PyQt6.QtWidgets import QDialog, QVBoxLayout
        dlg = QDialog(self)
        dlg.setWindowTitle("Help")
        t = self.theme
        dlg.setStyleSheet(f"background-color: {t.bg}; color: {t.text_primary};")
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(16, 12, 16, 12)
        lbl = QLabel(
            "<b>Settings</b><br><br>"
            "Press + or drag images/folders into the window<br>"
            "to add files<br><br>"
            "<b>Slideshow</b><br><br>"
            "<table>"
            "<tr><td>Space&nbsp;&nbsp;</td><td>pause / resume</td></tr>"
            "<tr><td>\u2190 \u2192&nbsp;&nbsp;</td><td>previous / next</td></tr>"
            "<tr><td>F11&nbsp;&nbsp;</td><td>fullscreen</td></tr>"
            "<tr><td>Esc&nbsp;&nbsp;</td><td>exit fullscreen</td></tr>"
            "<tr><td>? or H&nbsp;&nbsp;</td><td>help</td></tr>"
            "</table><br>"
            "RMB + drag — move window<br>"
            "Window edges — resize"
        )
        lbl.setStyleSheet(f"color: {t.text_primary}; font-size: 11px;")
        lbl.setWordWrap(True)
        layout.addWidget(lbl)
        dlg.adjustSize()
        dlg.exec()

    def _toggle_theme(self):
        self.theme.toggle()
        self._apply_theme()

    def _pick_accent(self):
        from PyQt6.QtWidgets import QColorDialog
        color = QColorDialog.getColor(
            QColor(self.theme.accent), self, "Accent color")
        if color.isValid():
            self.theme.accent = color.name()
            self._apply_theme()

    # ------------------------------------------------------------------ Toggle methods

    def _toggle_topmost(self):
        self._topmost = not self._topmost
        t = self.theme
        _icon = Icons.TOPMOST_ON if self._topmost else Icons.TOPMOST_OFF
        _color = t.accent if self._topmost else t.text_hint
        self._topmost_btn.setIcon(qta.icon(_icon, color=_color))
        # Apply always-on-top flag to this window
        flags = self.windowFlags()
        if self._topmost:
            self.setWindowFlags(flags | Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(flags & ~Qt.WindowType.WindowStaysOnTopHint)
        self.show()

    def _toggle_random(self):
        self._random = not self._random
        t = self.theme
        _icon = Icons.RANDOM_ON if self._random else Icons.RANDOM_OFF
        _color = t.accent if self._random else t.text_hint
        self._dice_btn.setIcon(qta.icon(_icon, color=_color))

    # ------------------------------------------------------------------ Mode

    def _set_timer_mode(self, mode):
        self._timer_mode = mode
        if mode == "quick":
            # Show quick buttons, hide class buttons
            for btn, _ in self._quick_btns:
                btn.show()
            for btn, _ in self._class_btns:
                btn.hide()
            # Apply uniform timer to all images
            timer = self.get_timer_seconds()
            for img in self.images:
                img.timer = timer
        else:
            # Show class buttons, hide quick buttons
            for btn, _ in self._quick_btns:
                btn.hide()
            for btn, _ in self._class_btns:
                btn.show()
        self._update_mode_buttons()
        self._update_summary()
        self._apply_theme()  # refreshes duration picker color
        if self._editor_panel is not None and self._dock_mode == "right":
            self._editor_panel.refresh(self.images)

    def _update_mode_buttons(self):
        t = self.theme
        active_s = (
            f"background-color: {t.bg_active}; color: {t.text_primary}; "
            f"border: 1px solid {t.border_active}; "
            f"font-size: {S.FONT_BUTTON}px; font-weight: 500; padding: 2px 8px;")
        inactive_s = (
            f"background-color: {t.bg}; color: {t.text_secondary}; "
            f"border: 1px solid {t.border}; "
            f"font-size: {S.FONT_BUTTON}px; font-weight: 500; padding: 2px 8px;")
        if self._timer_mode == "class":
            self._class_btn.setStyleSheet(active_s)
            self._quick_btn.setStyleSheet(inactive_s)
        else:
            self._class_btn.setStyleSheet(inactive_s)
            self._quick_btn.setStyleSheet(active_s)

    # ------------------------------------------------------------------ Quick timer (presets)

    def _select_preset_by_secs(self, secs):
        for i, (s, _) in enumerate(TIMER_PRESETS):
            if s == secs:
                self._preset_index = i
                for img in self.images:
                    img.timer = s
                self._update_preset_styles()
                self._update_summary()
                if self._editor_panel is not None and self._dock_mode == "right":
                    self._editor_panel.refresh(self.images)
                return

    def _update_preset_styles(self):
        t = self.theme
        current_secs = TIMER_PRESETS[self._preset_index][0]
        for btn, secs in self._quick_btns:
            is_active = secs == current_secs
            if is_active:
                btn.setStyleSheet(
                    f"background-color: {t.bg_active}; color: {t.text_primary}; "
                    f"border: 1px solid {t.border_active}; "
                    f"font-size: {S.FONT_BUTTON}px; "
                    f"padding: {S.TIMER_BTN_PADDING_V}px {S.TIMER_BTN_PADDING_H}px;")
            else:
                btn.setStyleSheet(
                    f"background-color: {t.bg_button}; color: {t.text_secondary}; "
                    f"border: 1px solid {t.border}; "
                    f"font-size: {S.FONT_BUTTON}px; "
                    f"padding: {S.TIMER_BTN_PADDING_V}px {S.TIMER_BTN_PADDING_H}px;")

    def get_timer_seconds(self):
        return TIMER_PRESETS[self._preset_index][0]

    # ------------------------------------------------------------------ Class timer (session duration)

    def _prev_session(self):
        if self._session_index > 0:
            self._session_index -= 1
            self._update_session_display()
            if self.images:
                self._auto_distribute()

    def _next_session(self):
        if self._session_index < len(SESSION_PRESETS) - 1:
            self._session_index += 1
            self._update_session_display()
            if self.images:
                self._auto_distribute()

    def _update_session_display(self):
        secs, _ = SESSION_PRESETS[self._session_index]
        self._ses_display.setText(format_time(secs))

    def _get_session_seconds(self):
        return SESSION_PRESETS[self._session_index][0]

    # ------------------------------------------------------------------ Tiers (class mode)

    def _on_tier_clicked(self, secs):
        """Handle tier button click — update active state and trigger auto-distribute."""
        # Find the button and sync its internal checked state
        for btn, s in self._class_btns:
            if s == secs:
                # isChecked() already toggled by Qt (button is checkable)
                break
        self._update_tier_styles()
        if self.images:
            self._auto_distribute()

    def _get_selected_tiers(self):
        tiers = []
        for btn, secs in self._class_btns:
            if btn.isChecked():
                # find label from ALL_TIERS
                for s, label in ALL_TIERS:
                    if s == secs:
                        tiers.append((secs, label))
                        break
        return tiers if tiers else None

    def _update_tier_styles(self):
        t = self.theme
        for btn, secs in self._class_btns:
            if btn.isChecked():
                btn.setStyleSheet(
                    f"background-color: {t.bg_active}; color: {t.text_primary}; "
                    f"border: 1px solid {t.border_active}; "
                    f"font-size: {S.FONT_BUTTON}px; "
                    f"padding: {S.TIMER_BTN_PADDING_V}px {S.TIMER_BTN_PADDING_H}px;")
            else:
                btn.setStyleSheet(
                    f"background-color: {t.bg_button}; color: {t.text_secondary}; "
                    f"border: 1px solid {t.border}; "
                    f"font-size: {S.FONT_BUTTON}px; "
                    f"padding: {S.TIMER_BTN_PADDING_V}px {S.TIMER_BTN_PADDING_H}px;")

    # ------------------------------------------------------------------ Auto-distribute

    def _reset_groups(self):
        self._manual_groups = []
        self._class_groups = []
        self._update_groups_display()
        self._update_summary()

    def _apply_class_timers(self):
        if self._class_groups:
            timers = groups_to_timers(self._class_groups)
            for i, img in enumerate(self.images):
                # Skip pinned files during auto-distribution
                if getattr(img, "pinned", False):
                    continue
                img.timer = timers[i] if i < len(timers) else 0
        if self._editor_panel is not None and self._dock_mode == "right":
            self._editor_panel.refresh(self.images)

    def _auto_distribute(self):
        if not self.images:
            return
        total_secs = self._get_session_seconds()
        manual_time = total_duration(self._manual_groups)
        manual_images = sum(c for c, _ in self._manual_groups)
        remaining_time = max(0, total_secs - manual_time)
        remaining_images = max(0, len(self.images) - manual_images)

        if remaining_images > 0 and remaining_time > 0:
            auto_groups = auto_distribute(remaining_images, remaining_time,
                                          custom_tiers=self._get_selected_tiers())
        else:
            auto_groups = []

        combined = self._manual_groups + auto_groups
        combined.sort(key=lambda g: g[1])
        self._class_groups = combined
        self._apply_class_timers()
        self._update_groups_display()
        self._update_summary()

    def _update_groups_display(self):
        if not self._class_groups:
            self._groups_label.setText("")
            self._total_label.setText("")
            return
        parts = []
        for count, timer in self._class_groups:
            if timer >= 3600:
                t = f"{timer // 3600}h"
            elif timer >= 60:
                t = f"{timer // 60}m"
            else:
                t = f"{timer}s"
            parts.append(f"{count}x{t}")
        self._groups_label.setText("  ".join(parts))
        dur = total_duration(self._class_groups)
        self._total_label.setText(format_time(dur))

    # ------------------------------------------------------------------ Image count

    def _update_img_count(self):
        n = len(self.images)
        self._img_count_label.setText(f"{n} img")

    # ------------------------------------------------------------------ Summary

    def _update_summary(self):
        n = len(self.images)
        if self._timer_mode == "quick":
            if n == 0:
                self._groups_label.setText("")
                self._total_label.setText("")
            else:
                total = n * self.get_timer_seconds()
                self._groups_label.setText(f"{n} images")
                self._total_label.setText(format_time(total))
        else:
            if n == 0:
                self._groups_label.setText("")
                self._total_label.setText("")
            elif self._class_groups:
                self._update_groups_display()
            else:
                self._groups_label.setText(f"{n} images")
                self._total_label.setText("")

    # ------------------------------------------------------------------ Image management

    def _add_files(self):
        exts = " ".join(f"*{e}" for e in SUPPORTED_FORMATS)
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select files", "",
            f"Images ({exts});;All files (*)"
        )
        if paths:
            timer = self.get_timer_seconds()
            for p in filter_image_files(paths):
                self.images.append(ImageItem(path=p, timer=timer))
            self._on_images_changed()

    def _add_folder(self, folder):
        timer = self.get_timer_seconds()
        for p in scan_folder(folder):
            self.images.append(ImageItem(path=p, timer=timer))
        self._on_images_changed()

    def _on_images_changed(self):
        self._update_img_count()
        self._update_summary()
        self.images_changed.emit()
        if self._editor_panel is not None and self._dock_mode == "right":
            self._editor_panel.refresh(self.images)

    def _open_editor(self):
        """Open the editor panel docked to the right of the settings window."""
        if self._dock_mode == "right":
            return
        if self._dock_mode == "detached":
            if self.editor and self.editor.isVisible():
                self.editor.raise_()
                return

        if self._editor_panel is None:
            from ui.editor_panel import EditorPanel
            view = getattr(self, "_last_editor_view", "list")
            self._editor_panel = EditorPanel(
                self.images, self.theme, parent=self, view_mode=view)
            self._editor_panel.images_updated.connect(self._on_editor_update)
            self._editor_panel.close_requested.connect(self._close_editor)
            self._editor_panel.detach_requested.connect(self._detach_editor)
            layout = QVBoxLayout(self._editor_container)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            layout.addWidget(self._editor_panel)
        else:
            self._editor_panel.refresh(self.images)

        self._dock_divider.show()
        self._editor_container.show()
        self.setFixedSize(S.MAIN_W + 1 + S.EDITOR_W, S.MAIN_H)
        self._dock_mode = "right"

    def _close_editor(self):
        """Collapse the docked editor and restore original window size."""
        if self._editor_panel is not None:
            self._last_editor_view = self._editor_panel._view_mode
        self._dock_divider.hide()
        self._editor_container.hide()
        self.setFixedSize(S.MAIN_W, S.MAIN_H)
        self._dock_mode = "compact"

    def _detach_editor(self):
        """Detach the editor into a standalone floating window."""
        if self._editor_panel is not None:
            self._last_editor_view = self._editor_panel._view_mode
        self._dock_divider.hide()
        self._editor_container.hide()
        self.setFixedSize(S.MAIN_W, S.MAIN_H)
        self._dock_mode = "detached"
        from ui.image_editor_window import ImageEditorWindow
        view = getattr(self, "_last_editor_view", "list")
        self.editor = ImageEditorWindow(self.images, self.theme, parent=self, view_mode=view)
        self.editor.images_updated.connect(self._on_editor_update)
        self.editor.show()

    def _on_editor_update(self, images):
        self.images = images
        self._update_img_count()
        self._update_summary()

    # ------------------------------------------------------------------ Drag and drop

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        paths = [u.toLocalFile() for u in urls]
        timer = self.get_timer_seconds()
        added = 0
        for p in paths:
            if os.path.isdir(p):
                for fp in scan_folder(p):
                    self.images.append(ImageItem(path=fp, timer=timer))
                    added += 1
            elif os.path.isfile(p) and os.path.splitext(p)[1].lower() in SUPPORTED_FORMATS:
                self.images.append(ImageItem(path=p, timer=timer))
                added += 1
        if added:
            self._on_images_changed()
        event.acceptProposedAction()

    # ------------------------------------------------------------------ Slideshow

    def _start_slideshow(self):
        if not self.images:
            return

        show_images = self.images
        if self._timer_mode == "class" and self._class_groups:
            timers = groups_to_timers(self._class_groups)
            show_images = []
            for i, img in enumerate(self.images):
                if i < len(timers):
                    img.timer = timers[i]
                    show_images.append(img)

        settings = {
            "order": "random" if self._random else "sequential",
            "topmost": self._topmost,
            "viewer_size": getattr(self, "_last_viewer_size", None),
        }
        from ui.viewer_window import ViewerWindow
        self.viewer = ViewerWindow(show_images, settings, on_close=self._on_viewer_closed)
        self.viewer.show()
        self.hide()

    def _on_viewer_closed(self, return_only=False):
        if self.viewer and not self.viewer.isFullScreen():
            self._last_viewer_size = [self.viewer.width(), self.viewer.height()]
        if return_only:
            self.show()
        else:
            self.viewer = None
            self.show()

    # ------------------------------------------------------------------ Session save/restore

    def _restore_session(self):
        data = load_session()
        if not data:
            return
        images_data = data.get("images", [])
        self.images = [ImageItem.from_dict(d) for d in images_data]
        self.images = [img for img in self.images if os.path.isfile(img.path)]

        timer_secs = data.get("timer_seconds", 300)
        for i, (s, _) in enumerate(TIMER_PRESETS):
            if s == timer_secs:
                self._preset_index = i
                break

        # Map old session file mode names to new names
        saved_mode = data.get("timer_mode", "quick")
        if saved_mode == "standard":
            self._timer_mode = "quick"
        elif saved_mode == "class":
            self._timer_mode = "class"
        elif saved_mode == "session":
            self._timer_mode = "class"
        else:
            self._timer_mode = "quick"

        session_secs = data.get("session_seconds")
        if session_secs:
            for i, (s, _) in enumerate(SESSION_PRESETS):
                if s == session_secs:
                    self._session_index = i
                    break

        self._random = data.get("random_order", False)
        self._topmost = data.get("topmost", False)

        saved_tiers = data.get("tiers")
        if saved_tiers is not None:
            for btn, secs in self._class_btns:
                active = secs in saved_tiers
                btn.setChecked(active)
            self._update_tier_styles()

        self._last_editor_view = data.get("editor_view", "list")
        self._last_viewer_size = data.get("viewer_size")
        saved_dock = data.get("dock_mode", "compact")
        # Only restore compact or right; detached requires user action
        if saved_dock == "right" and self.images:
            QTimer.singleShot(100, self._open_editor)

        theme_name = data.get("theme", "dark")
        accent = data.get("accent")
        if accent:
            self.theme.accent = accent
        if theme_name != self.theme.name:
            self.theme.toggle()

        self._apply_theme()
        self._update_preset_styles()
        self._update_session_display()
        self._set_timer_mode(self._timer_mode)
        self._update_img_count()
        self._update_summary()

    def _save_session(self):
        # Map new mode names back to the canonical storage keys
        if self._timer_mode == "class":
            saved_mode = "class"
        else:
            saved_mode = "standard"

        data = {
            "images": [img.to_dict() for img in self.images],
            "timer_seconds": self.get_timer_seconds(),
            "timer_mode": saved_mode,
            "session_seconds": self._get_session_seconds(),
            "random_order": self._random,
            "topmost": self._topmost,
            "theme": self.theme.name,
            "accent": self.theme.accent,
            "tiers": [secs for btn, secs in self._class_btns if btn.isChecked()],
            "editor_view": (
                self._editor_panel._view_mode if self._editor_panel is not None and self._dock_mode == "right"
                else getattr(self, "_last_editor_view", "list")
            ),
            "viewer_size": getattr(self, "_last_viewer_size", None),
            "dock_mode": self._dock_mode,
        }
        save_session(data)

    # ------------------------------------------------------------------ Close

    def closeEvent(self, event):
        if self.viewer is not None:
            event.ignore()
            self.hide()
            self.viewer.show()
        else:
            self._save_session()
            event.accept()
