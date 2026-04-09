import os
import random
import qtawesome as qta
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                              QPushButton, QLabel, QFileDialog, QScrollArea,
                              QSizePolicy, QApplication, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QColor
from core.constants import SUPPORTED_FORMATS, TIMER_PRESETS, SESSION_LIMIT_PRESETS
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
from ui.snap import SnapMixin


ALL_TIERS = [(30, "30s"), (60, "1m"), (180, "3m"),
             (300, "5m"), (600, "10m"), (900, "15m"),
             (1800, "30m"), (3600, "1h")]


class SettingsWindow(QMainWindow, SnapMixin):
    images_changed = pyqtSignal()

    def __init__(self):
        QMainWindow.__init__(self)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setWindowTitle("RefBot")
        self.setFixedSize(S.MAIN_W, S.MAIN_H)

        self.images = []
        self.viewer = None
        self.editor = None
        self.theme = Theme("dark")

        # "quick" replaces old "standard", "class" replaces old "session"
        self._timer_mode = "quick"
        self._preset_index = 3   # default 5min
        self._session_limit_index = 0  # default: no limit
        self._class_groups = []

        self._topmost = False
        self._shuffle = True

        self._build_ui()
        self._apply_theme()
        SnapMixin.__init__(self)
        self._restore_session()
        self.setAcceptDrops(True)

    @property
    def _editor_visible(self):
        return self.editor is not None and self.editor.isVisible()

    # ------------------------------------------------------------------ UI

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
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
        root.addStretch()

        # ── 2. Mode row + image count ──────────────────────────────────────
        mode_row = QHBoxLayout()
        mode_row.setSpacing(0)
        mode_row.setContentsMargins(0, 0, 0, 0)

        self._class_btn = QPushButton("Class")
        self._class_btn.setFixedHeight(34)
        self._class_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._class_btn.clicked.connect(lambda: self._set_timer_mode("class"))

        self._quick_btn = QPushButton("Quick")
        self._quick_btn.setFixedHeight(34)
        self._quick_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._quick_btn.clicked.connect(lambda: self._set_timer_mode("quick"))

        self._add_btn = make_icon_btn(Icons.PLUS, self.theme.text_hint,
                                      size=S.ICON_HEADER, tooltip="Add files")
        self._add_btn.clicked.connect(self._open_editor)

        mode_row.addWidget(self._class_btn, 1)
        mode_row.addSpacing(4)
        mode_row.addWidget(self._quick_btn, 1)
        root.addLayout(mode_row)
        root.addSpacing(S.SPACING_MODE)

        # ── 3. Timer buttons (2 rows × 4) ──────────────────────────────────
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

        # ── 4. Stretch — separates upper (config) and lower (summary+start)
        root.addStretch()

        # ── 5. Bottom group: summary left + start right ──────────────────
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(0)
        bottom_row.setContentsMargins(0, 0, 0, 0)

        # Summary info (left side) — wrapped in a widget for AlignBottom
        summary_widget = QWidget()
        summary_col = QVBoxLayout(summary_widget)
        summary_col.setSpacing(0)
        summary_col.setContentsMargins(0, 0, 0, 0)

        self._groups_label = QLabel("")
        self._groups_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._groups_label.setWordWrap(True)
        self._groups_label.setMaximumWidth(150)
        summary_col.addWidget(self._groups_label)

        summary_time = QHBoxLayout()
        summary_time.setSpacing(4)
        summary_time.setContentsMargins(0, 0, 0, 0)

        self._total_label = QLabel("")
        self._total_label.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self._limit_sep = QLabel("\u00b7")
        self._limit_sep.hide()

        self._limit_btn = QPushButton("no limit")
        self._limit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._limit_btn.setToolTip("Session time limit")
        self._limit_btn.clicked.connect(self._next_limit)
        self._limit_btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._limit_btn.customContextMenuRequested.connect(self._prev_limit)
        self._limit_btn.hide()

        summary_time.addWidget(self._total_label)
        summary_time.addWidget(self._limit_sep)
        summary_time.addWidget(self._limit_btn)
        summary_time.addStretch()

        summary_col.addLayout(summary_time)

        # Start button (right side)
        self._start_btn = make_start_btn(self.theme)
        self._start_btn.clicked.connect(self._start_slideshow)

        bottom_row.addWidget(summary_widget, alignment=Qt.AlignmentFlag.AlignBottom)
        bottom_row.addStretch()
        bottom_row.addWidget(self._add_btn, alignment=Qt.AlignmentFlag.AlignBottom)
        bottom_row.addSpacing(8)
        bottom_row.addWidget(self._start_btn, alignment=Qt.AlignmentFlag.AlignBottom)

        root.addLayout(bottom_row)

        # ── Initialize display ─────────────────────────────────────────────
        self._update_mode_buttons()
        self._update_preset_styles()
        self._update_summary()


    # ------------------------------------------------------------------ Theme

    def _apply_theme(self):
        t = self.theme
        self.setStyleSheet(f"background-color: {t.bg}; color: {t.text_primary};")

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

        self._add_btn.setIcon(qta.icon(Icons.PLUS, color=t.text_hint))
        self._add_btn.setStyleSheet("background: transparent; border: none; padding: 0px;")

        # Timer buttons
        self._update_preset_styles()
        self._update_tier_styles()

        # Summary
        self._groups_label.setStyleSheet(
            f"color: {t.text_secondary}; font-size: {S.FONT_HINT}px; font-weight: 500;")
        self._total_label.setStyleSheet(
            f"color: {t.text_secondary}; font-size: {S.FONT_TOTAL}px; font-weight: 500;")
        self._limit_sep.setStyleSheet(f"color: {t.text_hint}; font-size: 10px;")
        self._update_limit_display()

        # Bottom bar
        # Refresh start button
        self._start_btn.setIcon(qta.icon(Icons.START, color=t.start_text))
        self._start_btn.setStyleSheet(
            f"background-color: {t.start_bg}; border: none; "
            f"border-radius: {int(S.ICON_START * S.START_RADIUS_RATIO)}px;")

        self._dismiss_help()

    # ------------------------------------------------------------------ Window dragging

    def mousePressEvent(self, event):
        self.snap_mouse_press(event)

    def mouseMoveEvent(self, event):
        self.snap_mouse_move(event)

    def mouseReleaseEvent(self, event):
        self.snap_mouse_release(event)

    # ------------------------------------------------------------------ Help / Theme / Accent

    def _dismiss_help(self):
        if hasattr(self, "_help_overlay") and self._help_overlay is not None:
            self._help_overlay.deleteLater()
            self._help_overlay = None

    def _show_help(self):
        if hasattr(self, "_help_overlay") and self._help_overlay is not None:
            self._dismiss_help()
            return
        t = self.theme
        cw = self.centralWidget()
        overlay = QWidget(cw)
        overlay.setGeometry(cw.rect())
        overlay.setStyleSheet(f"background-color: rgba({t.bg_rgb}, 230);")

        layout = QVBoxLayout(overlay)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet(
            f"QScrollArea {{ background: transparent; }}"
            f"QScrollBar:vertical {{ width: 4px; background: transparent; }}"
            f"QScrollBar::handle:vertical {{ background: {t.text_hint}; }}"
            f"QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}")
        scroll.mousePressEvent = lambda e: self._dismiss_help()

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        content.mousePressEvent = lambda e: self._dismiss_help()
        inner = QVBoxLayout(content)
        inner.setContentsMargins(16, 14, 16, 12)

        lbl = QLabel(
            "<b>Settings</b><br>"
            "Drag files/folders into the window to add images<br>"
            "+ button — open editor (reorder, delete, pin)<br>"
            "Quick — same timer for all images<br>"
            "Class — auto-distribute by tiers, optional session limit<br>"
            "Pencil button — start slideshow<br><br>"
            "<b>Slideshow</b><br>"
            "<table>"
            "<tr><td>Space&nbsp;&nbsp;</td><td>pause / resume</td></tr>"
            "<tr><td>\u2190 \u2192&nbsp;&nbsp;</td><td>prev / next</td></tr>"
            "<tr><td>F11&nbsp;&nbsp;</td><td>fullscreen</td></tr>"
            "<tr><td>Esc&nbsp;&nbsp;</td><td>exit fullscreen</td></tr>"
            "<tr><td>H&nbsp;&nbsp;</td><td>help</td></tr>"
            "</table><br>"
            "RMB + drag — move window<br>"
            "Edges — resize<br><br>"
            "<b>Header</b><br>"
            "Pin — always on top<br>"
            "Dot — accent color<br>"
            "Sun/Moon — toggle theme<br><br>"
            "<span style='color: {hint}'>Click anywhere to close</span>".format(
                hint=t.text_hint)
        )
        lbl.setStyleSheet(f"color: {t.text_primary}; font-size: 11px;")
        lbl.setWordWrap(True)
        lbl.mousePressEvent = lambda e: self._dismiss_help()
        inner.addWidget(lbl)
        inner.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll)

        overlay.raise_()
        overlay.show()
        self._help_overlay = overlay

    def _toggle_theme(self):
        self.theme.toggle()
        self._apply_theme()
        self._refresh_editor_theme()

    def _pick_accent(self):
        from PyQt6.QtWidgets import QColorDialog
        color = QColorDialog.getColor(
            QColor(self.theme.accent), self, "Accent color")
        if color.isValid():
            self.theme.accent = color.name()
            self._apply_theme()
            self._refresh_editor_theme()

    def _refresh_editor_theme(self):
        if self._editor_visible:
            self.editor.theme = self.theme
            self.editor._apply_theme()
            self.editor._panel.theme = self.theme
            self.editor._panel._apply_theme()
            self.editor._panel._rebuild()

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

    # ------------------------------------------------------------------ Mode

    def _set_timer_mode(self, mode):
        self._timer_mode = mode
        if mode == "quick":
            for btn, _ in self._quick_btns:
                btn.show()
            for btn, _ in self._class_btns:
                btn.hide()
            timer = self.get_timer_seconds()
            for img in self.images:
                img.timer = timer
        else:
            for btn, _ in self._quick_btns:
                btn.hide()
            for btn, _ in self._class_btns:
                btn.show()
        self._update_mode_buttons()
        self._update_summary()
        self._apply_theme()
        if self._editor_visible:
            self.editor.refresh(self.images)

    def _update_mode_buttons(self):
        t = self.theme
        active_s = (
            f"background-color: {t.bg_active}; color: {t.text_primary}; "
            f"border: 1px solid {t.border_active}; "
            f"font-size: {S.FONT_MODE}px; font-weight: 500; padding: 4px 8px;")
        inactive_s = (
            f"background-color: {t.bg}; color: {t.text_secondary}; "
            f"border: 1px solid {t.border}; "
            f"font-size: {S.FONT_MODE}px; font-weight: 500; padding: 4px 8px;")
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
                if self._editor_visible:
                    self.editor.refresh(self.images)
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

    # ------------------------------------------------------------------ Session limit

    def _next_limit(self):
        self._session_limit_index = (self._session_limit_index + 1) % len(SESSION_LIMIT_PRESETS)
        self._update_limit_display()

    def _prev_limit(self, pos=None):
        self._session_limit_index = (self._session_limit_index - 1) % len(SESSION_LIMIT_PRESETS)
        self._update_limit_display()

    def _get_session_limit(self):
        return SESSION_LIMIT_PRESETS[self._session_limit_index][0]

    def _update_limit_display(self):
        secs, label = SESSION_LIMIT_PRESETS[self._session_limit_index]
        t = self.theme
        if secs is None:
            self._limit_btn.setText("no limit")
            self._limit_btn.setStyleSheet(
                f"color: {t.text_hint}; font-size: 9px; font-weight: 500; "
                f"background: transparent; border: none; padding: 0;")
        else:
            self._limit_btn.setText(f"limit: {label}")
            self._limit_btn.setStyleSheet(
                f"color: {t.accent}; font-size: 9px; font-weight: 500; "
                f"background: transparent; border: none; padding: 0; "
                f"text-decoration: underline;")

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

    def _apply_class_timers(self):
        if self._class_groups:
            timers = groups_to_timers(self._class_groups)
            for i, img in enumerate(self.images):
                if getattr(img, "pinned", False):
                    continue
                img.timer = timers[i] if i < len(timers) else timers[-1]
        if self._editor_visible:
            self.editor.refresh(self.images)

    def _auto_distribute(self):
        if not self.images:
            return
        self._class_groups = auto_distribute(
            len(self.images), custom_tiers=self._get_selected_tiers())
        self._apply_class_timers()
        self._update_groups_display()
        self._update_summary()

    def _update_groups_display(self):
        if not self._class_groups:
            self._groups_label.setText("")
            self._total_label.setText("")
            self._limit_sep.hide()
            self._limit_btn.hide()
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
        self._limit_sep.show()
        self._limit_btn.show()
        self._update_limit_display()

    # ------------------------------------------------------------------ Summary

    def _update_summary(self):
        n = len(self.images)
        if self._timer_mode == "quick":
            if n == 0:
                self._groups_label.setText("")
                self._total_label.setText("")
                self._limit_sep.hide()
                self._limit_btn.hide()
            else:
                total = n * self.get_timer_seconds()
                self._groups_label.setText(f"{n} images")
                self._total_label.setText(format_time(total))
                self._limit_sep.show()
                self._limit_btn.show()
                self._update_limit_display()
        else:
            if n == 0:
                self._groups_label.setText("")
                self._total_label.setText("")
                self._limit_sep.hide()
                self._limit_btn.hide()
            elif self._class_groups:
                self._update_groups_display()
            else:
                self._groups_label.setText(f"{n} images")
                self._total_label.setText("")
                self._limit_sep.hide()
                self._limit_btn.hide()

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

        self._update_summary()
        self.images_changed.emit()
        if self._editor_visible:
            self.editor.refresh(self.images)

    def _open_editor(self):
        """Open the editor as a separate window, snapped to the right."""
        if self._editor_visible:
            self.editor.raise_()
            return
        from ui.image_editor_window import ImageEditorWindow
        view = getattr(self, "_last_editor_view", "list")
        self.editor = ImageEditorWindow(
            self.images, self.theme, parent=self, view_mode=view, shuffle=self._shuffle)
        self.editor.images_updated.connect(self._on_editor_update)
        self.editor.shuffle_changed.connect(self._on_shuffle_changed)
        # Position to the right and auto-snap
        pos = self.geometry()
        self.editor.move(pos.right() + 1, pos.top())
        self.editor.resize(S.EDITOR_W, S.MAIN_H)
        self.editor.show()
        # Establish snap relationship
        self.editor._snapped_to = (self, "right")
        self._snapped_children.append((self.editor, "right"))

    def _on_editor_close(self):
        """Called when the editor window is closed."""
        if self.editor is not None:
            self._last_editor_view = self.editor._view_mode
        self.editor = None

    def _on_shuffle_changed(self, value):
        self._shuffle = value

    def _on_editor_update(self, images):
        self.images = list(images)

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

        # Shuffle unpinned images for variety (if enabled), then assign timers
        if self._shuffle:
            pinned = [img for img in self.images if img.pinned]
            unpinned = [img for img in self.images if not img.pinned]
            random.shuffle(unpinned)
            show_images = unpinned + pinned
        else:
            show_images = list(self.images)

        if self._timer_mode == "quick":
            timer = self.get_timer_seconds()
            for img in show_images:
                if not img.pinned:
                    img.timer = timer
        elif self._class_groups:
            timers = groups_to_timers(self._class_groups)
            idx = 0
            for img in show_images:
                if not img.pinned and idx < len(timers):
                    img.timer = timers[idx]
                    idx += 1
            # Sort by timer so slideshow goes from short to long poses
            show_images.sort(key=lambda img: img.timer)

        settings = {
            "order": "sequential",
            "topmost": self._topmost,
            "viewer_size": getattr(self, "_last_viewer_size", None),
            "session_limit": self._get_session_limit(),
        }
        from ui.viewer_window import ViewerWindow
        self.viewer = ViewerWindow(show_images, settings, on_close=self._on_viewer_closed)
        self.viewer.show()
        # Hide editor window too
        if self._editor_visible:
            self.editor.hide()
        self.hide()

    def _on_viewer_closed(self, return_only=False):
        if self.viewer and not self.viewer.isFullScreen():
            self._last_viewer_size = [self.viewer.width(), self.viewer.height()]
        if return_only:
            self.show()
        else:
            self.viewer = None
            self.show()
        # Restore editor if it was hidden
        if self.editor is not None and not self._editor_visible:
            self.editor.show()

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
        _MODE_MAP = {"standard": "quick", "session": "class", "class": "class"}
        self._timer_mode = _MODE_MAP.get(data.get("timer_mode", "quick"), "quick")

        session_limit = data.get("session_limit")
        if session_limit is not None:
            for i, (s, _) in enumerate(SESSION_LIMIT_PRESETS):
                if s == session_limit:
                    self._session_limit_index = i
                    break
        else:
            self._session_limit_index = 0

        self._topmost = data.get("topmost", False)
        self._shuffle = data.get("shuffle", True)

        saved_tiers = data.get("tiers")
        if saved_tiers is not None:
            for btn, secs in self._class_btns:
                active = secs in saved_tiers
                btn.setChecked(active)
            self._update_tier_styles()

        self._last_editor_view = data.get("editor_view", "list")
        self._last_viewer_size = data.get("viewer_size")

        theme_name = data.get("theme", "dark")
        accent = data.get("accent")
        if accent:
            self.theme.accent = accent
        if theme_name != self.theme.name:
            self.theme.toggle()

        self._apply_theme()
        self._update_preset_styles()
        self._set_timer_mode(self._timer_mode)
        # Rebuild class-mode groups so images get proper timers
        if self._timer_mode == "class" and self.images:
            self._auto_distribute()

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
            "session_limit": self._get_session_limit(),
            "topmost": self._topmost,
            "shuffle": self._shuffle,
            "theme": self.theme.name,
            "accent": self.theme.accent,
            "tiers": [secs for btn, secs in self._class_btns if btn.isChecked()],
            "editor_view": (
                self.editor._view_mode if self._editor_visible
                else getattr(self, "_last_editor_view", "list")
            ),
            "viewer_size": getattr(self, "_last_viewer_size", None),
            "editor_pos": [self.editor.x(), self.editor.y()] if self.editor and self.editor.isVisible() else None,
            "editor_size": [self.editor.width(), self.editor.height()] if self.editor and self.editor.isVisible() else None,
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
            if self.editor is not None:
                self.editor.close()
            self.snap_cleanup()
            event.accept()
