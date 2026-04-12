"""BottomBar — summary labels, session limit, add button, start button."""
import qtawesome as qta
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from core.constants import SESSION_LIMIT_PRESETS
from core.timer_logic import format_time
from core.class_mode import total_duration
from ui.scales import S
from ui.icons import Icons
from ui.widgets import make_start_btn


class BottomBar(QWidget):
    """Summary + session limit + add/start buttons."""

    start_clicked = pyqtSignal()
    add_clicked = pyqtSignal()

    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._session_limit_index = 0

        self._build()

    # ------------------------------------------------------------------ Build

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # Summary info (left side)
        summary_widget = QWidget()
        summary_col = QVBoxLayout(summary_widget)
        summary_col.setSpacing(0)
        summary_col.setContentsMargins(0, 0, 0, 0)

        self._groups_label = QLabel("")
        self._groups_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._groups_label.setWordWrap(True)
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
        add_size = 26
        add_icon_sz = int(add_size * S.START_ICON_RATIO)
        add_radius = int(add_size * S.START_RADIUS_RATIO)
        self._add_btn = QPushButton()
        self._add_btn.setIcon(qta.icon(Icons.PLUS, color=self.theme.text_hint))
        self._add_btn.setIconSize(QSize(add_icon_sz, add_icon_sz))
        self._add_btn.setFixedSize(add_size, add_size)
        self._add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_btn.setToolTip("Add files")
        self._add_btn.setStyleSheet(
            f"background-color: {self.theme.bg_button}; border: none; "
            f"border-radius: {add_radius}px;")
        self._add_btn.clicked.connect(self.add_clicked.emit)

        self._start_btn = make_start_btn(self.theme)
        self._start_btn.clicked.connect(self.start_clicked.emit)

        layout.addWidget(summary_widget, 0, Qt.AlignmentFlag.AlignBottom)
        layout.addStretch()
        layout.addWidget(self._add_btn, 0, Qt.AlignmentFlag.AlignBottom)
        layout.addSpacing(8)
        layout.addWidget(self._start_btn, 0, Qt.AlignmentFlag.AlignBottom)

    # ------------------------------------------------------------------ Session limit

    def _next_limit(self):
        self._session_limit_index = (self._session_limit_index + 1) % len(SESSION_LIMIT_PRESETS)
        self._update_limit_display()

    def _prev_limit(self, pos=None):
        self._session_limit_index = (self._session_limit_index - 1) % len(SESSION_LIMIT_PRESETS)
        self._update_limit_display()

    def get_session_limit(self):
        return SESSION_LIMIT_PRESETS[self._session_limit_index][0]

    @property
    def session_limit_index(self):
        return self._session_limit_index

    @session_limit_index.setter
    def session_limit_index(self, value):
        self._session_limit_index = min(value, len(SESSION_LIMIT_PRESETS) - 1)

    def _update_limit_display(self):
        secs, label = SESSION_LIMIT_PRESETS[self._session_limit_index]
        t = self.theme
        if secs is None:
            self._limit_btn.setText("no limit")
            self._limit_btn.setStyleSheet(
                f"color: {t.text_hint}; font-size: 9px; font-weight: 500; "
                f"font-family: 'Lexend'; "
                f"background: transparent; border: none; padding: 0;")
        else:
            self._limit_btn.setText(f"limit: {label}")
            self._limit_btn.setStyleSheet(
                f"color: {t.accent}; font-size: 9px; font-weight: 500; "
                f"font-family: 'Lexend'; "
                f"background: transparent; border: none; padding: 0; "
                f"text-decoration: underline;")

    # ------------------------------------------------------------------ Summary updates

    def update_summary_quick(self, image_count, timer_seconds):
        if image_count == 0:
            self._groups_label.setText("")
            self._total_label.setText("")
            self._limit_sep.hide()
            self._limit_btn.hide()
        else:
            total = image_count * timer_seconds
            self._groups_label.setText(f"{image_count} images")
            self._total_label.setText(format_time(total))
            self._limit_sep.show()
            self._limit_btn.show()
            self._update_limit_display()

    def update_summary_class(self, image_count, class_groups):
        if image_count == 0:
            self._groups_label.setText("")
            self._total_label.setText("")
            self._limit_sep.hide()
            self._limit_btn.hide()
        elif class_groups:
            parts = []
            for count, timer in class_groups:
                if timer >= 3600:
                    t = f"{timer // 3600}h"
                elif timer >= 60:
                    t = f"{timer // 60}m"
                else:
                    t = f"{timer}s"
                parts.append(f"{count}x{t}")
            self._groups_label.setText("  ".join(parts))
            dur = total_duration(class_groups)
            self._total_label.setText(format_time(dur))
            self._limit_sep.show()
            self._limit_btn.show()
            self._update_limit_display()
        else:
            self._groups_label.setText(f"{image_count} images")
            self._total_label.setText("")
            self._limit_sep.hide()
            self._limit_btn.hide()

    # ------------------------------------------------------------------ Theme

    def apply_theme(self):
        t = self.theme
        self._groups_label.setStyleSheet(
            f"color: {t.text_secondary}; font-size: {S.FONT_HINT}px; font-weight: 500; "
            f"font-family: 'Lexend';")
        self._total_label.setStyleSheet(
            f"color: {t.text_secondary}; font-size: {S.FONT_TOTAL}px; font-weight: 500; "
            f"font-family: 'Lexend';")
        self._limit_sep.setStyleSheet(f"color: {t.text_hint}; font-size: 10px; font-family: 'Lexend';")
        self._update_limit_display()

        add_radius = int(self._add_btn.width() * S.START_RADIUS_RATIO)
        self._add_btn.setIcon(qta.icon(Icons.PLUS, color=t.text_hint))
        self._add_btn.setStyleSheet(
            f"background-color: {t.bg_button}; border: none; "
            f"border-radius: {add_radius}px;")
        self._start_btn.setIcon(qta.icon(Icons.START, color=t.start_text))
        self._start_btn.setStyleSheet(
            f"background-color: {t.start_bg}; border: none; "
            f"border-radius: {int(S.ICON_START * S.START_RADIUS_RATIO)}px;")

    # ------------------------------------------------------------------ Session save/restore

    def save_state(self):
        return {
            "session_limit": self.get_session_limit(),
        }

    def restore_state(self, data):
        session_limit = data.get("session_limit")
        if session_limit is not None:
            for i, (s, _) in enumerate(SESSION_LIMIT_PRESETS):
                if s == session_limit:
                    self._session_limit_index = i
                    break
        self._session_limit_index = min(self._session_limit_index,
                                        len(SESSION_LIMIT_PRESETS) - 1)
