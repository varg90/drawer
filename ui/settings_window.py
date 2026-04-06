import os
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                              QPushButton, QLabel, QCheckBox, QFileDialog,
                              QSizePolicy, QApplication, QStackedWidget)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QPainter, QColor, QPen
from core.constants import SUPPORTED_FORMATS, TIMER_PRESETS, SESSION_PRESETS
from core.timer_logic import format_time
from core.class_mode import auto_distribute, groups_to_timers, total_duration, format_group
from core.file_utils import filter_image_files, scan_folder
from core.session import save_session, load_session
from core.models import ImageItem
from ui.theme import Theme


ALL_TIERS = [(30, "30с"), (60, "1м"), (180, "3м"),
             (300, "5м"), (600, "10м"), (900, "15м"),
             (1800, "30м"), (3600, "1ч")]


class ThemeToggleButton(QPushButton):
    """Small circle split dark/light halves."""

    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setFixedSize(16, 16)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("background: transparent; border: none;")

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect().adjusted(1, 1, -1, -1)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#333"))
        p.drawChord(r, 90 * 16, 180 * 16)
        p.setBrush(QColor("#ccc"))
        p.drawChord(r, 270 * 16, 180 * 16)
        p.setPen(QPen(QColor(self.theme.border_active), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(r)
        p.end()


class SegmentButton(QPushButton):
    """One segment of a two-segment toggle."""
    pass


class PresetButton(QPushButton):
    """Small timer preset button."""
    pass


class TierToggle(QPushButton):
    """Toggleable tier button for session mode."""

    def __init__(self, text, seconds, parent=None):
        super().__init__(text, parent)
        self.seconds = seconds
        self._active = True
        self.setCheckable(True)
        self.setChecked(True)
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
        self.setWindowTitle("RefBot")
        self.setFixedWidth(360)
        self.images = []
        self.viewer = None
        self.editor = None
        self.theme = Theme("dark")

        self._timer_mode = "standard"
        self._preset_index = 2  # default 5min
        self._session_index = 5  # default 1h
        self._manual_groups = []
        self._class_groups = []

        self._build_ui()
        self._apply_theme()
        self._restore_session()
        self.setAcceptDrops(True)

        # Fix window size — QStackedWidget uses largest child height
        self._mode_stack.setCurrentWidget(self._session_widget)
        self.adjustSize()
        self.setFixedSize(self.size())
        self._set_timer_mode(self._timer_mode)

    # ------------------------------------------------------------------ UI

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(10)

        # 1. Header row: REFBOT + theme toggle
        header_row = QHBoxLayout()
        self._title = QLabel("REFBOT")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_row.addWidget(self._title, 1)
        self._theme_btn = ThemeToggleButton(self.theme)
        self._theme_btn.clicked.connect(self._toggle_theme)
        header_row.addWidget(self._theme_btn)
        root.addLayout(header_row)

        # 2. Drop zone
        self._drop_zone = QLabel("Перетащите изображения сюда\nили нажмите для выбора")
        self._drop_zone.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._drop_zone.setFixedHeight(70)
        self._drop_zone.setCursor(Qt.CursorShape.PointingHandCursor)
        self._drop_zone.mousePressEvent = lambda e: self._add_files()
        root.addWidget(self._drop_zone)

        # 3. Thumbnail strip + Edit button
        thumb_row = QHBoxLayout()
        thumb_row.setSpacing(2)
        self._thumb_labels = []
        for i in range(9):
            lbl = QLabel()
            lbl.setFixedSize(36, 36)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.hide()
            self._thumb_labels.append(lbl)
            thumb_row.addWidget(lbl)
        self._overflow_label = QLabel()
        self._overflow_label.setFixedSize(36, 36)
        self._overflow_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._overflow_label.hide()
        thumb_row.addWidget(self._overflow_label)
        thumb_row.addStretch()
        self._edit_btn = QPushButton("Edit")
        self._edit_btn.setFixedHeight(24)
        self._edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._edit_btn.clicked.connect(self._open_editor)
        thumb_row.addWidget(self._edit_btn)
        root.addLayout(thumb_row)

        # 4. Timer mode switch
        mode_row = QHBoxLayout()
        mode_row.setSpacing(0)
        self._standard_btn = SegmentButton("Быстрый")
        self._session_btn = SegmentButton("Сеанс")
        self._standard_btn.clicked.connect(lambda: self._set_timer_mode("standard"))
        self._session_btn.clicked.connect(lambda: self._set_timer_mode("session"))
        mode_row.addWidget(self._standard_btn)
        mode_row.addWidget(self._session_btn)
        root.addLayout(mode_row)

        # 5a. Standard mode content — preset buttons only
        self._standard_widget = QWidget()
        std_layout = QVBoxLayout(self._standard_widget)
        std_layout.setContentsMargins(0, 4, 0, 0)
        std_layout.setSpacing(3)

        preset_row1 = QHBoxLayout()
        preset_row1.addStretch()
        preset_row2 = QHBoxLayout()
        preset_row2.addStretch()
        self._preset_buttons = []
        row1_secs = {30, 60, 300, 600}  # 30с, 1м, 5м, 10м
        for secs, label in TIMER_PRESETS:
            btn = PresetButton(label.replace(" ", ""))
            btn.setCheckable(True)
            btn._secs = secs
            btn.clicked.connect(lambda checked, s=secs: self._select_preset_by_secs(s))
            self._preset_buttons.append(btn)
            if secs in row1_secs:
                preset_row1.addWidget(btn)
            else:
                preset_row2.addWidget(btn)
        preset_row1.addStretch()
        preset_row2.addStretch()
        std_layout.addLayout(preset_row1)
        std_layout.addLayout(preset_row2)

        # 5b. Session mode content
        self._session_widget = QWidget()
        ses_layout = QVBoxLayout(self._session_widget)
        ses_layout.setContentsMargins(0, 4, 0, 0)
        ses_layout.setSpacing(8)

        self._session_dur_label = QLabel("ДЛИТЕЛЬНОСТЬ СЕАНСА")
        self._session_dur_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ses_layout.addWidget(self._session_dur_label)

        sdur_row = QHBoxLayout()
        sdur_row.addStretch()
        self._ses_left = QPushButton("<")
        self._ses_left.setFixedSize(28, 28)
        self._ses_left.clicked.connect(self._prev_session)
        sdur_row.addWidget(self._ses_left)
        self._ses_display = QLabel("1:00:00")
        self._ses_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sdur_row.addWidget(self._ses_display)
        self._ses_right = QPushButton(">")
        self._ses_right.setFixedSize(28, 28)
        self._ses_right.clicked.connect(self._next_session)
        sdur_row.addWidget(self._ses_right)
        sdur_row.addStretch()
        ses_layout.addLayout(sdur_row)

        self._use_label = QLabel("ИСПОЛЬЗОВАТЬ")
        self._use_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ses_layout.addWidget(self._use_label)

        tier_row = QHBoxLayout()
        tier_row.addStretch()
        self._tier_toggles = []
        for secs, label in ALL_TIERS:
            btn = TierToggle(label, secs)
            btn.clicked.connect(self._update_tier_styles)
            self._tier_toggles.append(btn)
            tier_row.addWidget(btn)
        tier_row.addStretch()
        ses_layout.addLayout(tier_row)

        ses_layout.addSpacing(6)
        auto_row = QHBoxLayout()
        auto_row.addStretch()
        self._auto_btn = QPushButton("Авто-распределение")
        self._auto_btn.clicked.connect(self._auto_distribute)
        auto_row.addWidget(self._auto_btn)
        self._reset_btn = QPushButton("Сброс")
        self._reset_btn.clicked.connect(self._reset_groups)
        auto_row.addWidget(self._reset_btn)
        auto_row.addStretch()
        ses_layout.addLayout(auto_row)

        self._groups_label = QLabel("")
        self._groups_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ses_layout.addWidget(self._groups_label)

        self._mode_stack = QStackedWidget()
        self._mode_stack.addWidget(self._standard_widget)
        self._mode_stack.addWidget(self._session_widget)
        self._mode_stack.setCurrentWidget(self._standard_widget)
        root.addWidget(self._mode_stack)

        # 6. Random order checkbox
        root.addSpacing(2)
        random_row = QHBoxLayout()
        random_row.addStretch()
        self._random_cb = QCheckBox("Случайный порядок")
        random_row.addWidget(self._random_cb)
        random_row.addStretch()
        root.addLayout(random_row)

        # 7. Summary line
        self._summary = QLabel("")
        self._summary.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._summary.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self._summary)

        # 8. Always-on-top checkbox
        root.addSpacing(8)
        self._topmost_cb = QCheckBox("Поверх всех окон")
        root.addWidget(self._topmost_cb)

        # 9. Start button
        self._start_btn = QPushButton("СТАРТ")
        self._start_btn.setFixedHeight(40)
        self._start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._start_btn.clicked.connect(self._start_slideshow)
        root.addWidget(self._start_btn)

        root.addStretch()

        self._update_preset_styles()
        self._update_session_display()
        self._update_mode_buttons()

    # ------------------------------------------------------------------ Theme

    def _apply_theme(self):
        t = self.theme
        self.setStyleSheet(f"background-color: {t.bg}; color: {t.text_primary};")

        self._title.setStyleSheet(
            f"color: {t.text_header}; font-size: 12px; font-weight: 500; "
            f"letter-spacing: 3px;")

        self._drop_zone.setStyleSheet(
            f"background-color: {t.bg_secondary}; border: 1px dashed {t.border_active}; "
            f"color: {t.text_secondary}; font-size: 12px; font-weight: 500;")

        for lbl in self._thumb_labels:
            lbl.setStyleSheet(f"background-color: {t.bg_row_even};")
        self._overflow_label.setStyleSheet(
            f"background-color: {t.bg_row_even}; color: {t.text_secondary}; "
            f"font-size: 11px; font-weight: 500;")

        edit_s = (f"background-color: {t.bg_button}; color: {t.text_button}; "
                  f"border: 1px solid {t.border}; font-size: 10px; font-weight: 500; "
                  f"padding: 3px 6px;")
        self._edit_btn.setStyleSheet(edit_s)

        self._update_mode_buttons()

        arrow_s = (f"background-color: transparent; color: {t.text_secondary}; "
                   f"border: none; font-size: 16px; font-weight: bold;")
        self._ses_left.setStyleSheet(arrow_s)
        self._ses_right.setStyleSheet(arrow_s)

        self._ses_display.setStyleSheet(
            f"color: {t.text_primary}; font-size: 30px; font-weight: 400;")

        label_s = (f"color: {t.text_secondary}; font-size: 10px; font-weight: 500; "
                   f"letter-spacing: 2px;")
        self._session_dur_label.setStyleSheet(label_s)
        self._use_label.setStyleSheet(label_s)

        self._update_preset_styles()
        self._update_tier_styles()

        auto_s = (f"background-color: {t.bg_button}; color: {t.text_button}; "
                  f"border: 1px solid {t.border}; font-size: 11px; font-weight: 500; "
                  f"padding: 5px 14px;")
        self._auto_btn.setStyleSheet(auto_s)
        self._reset_btn.setStyleSheet(auto_s)

        self._groups_label.setStyleSheet(
            f"color: {t.text_secondary}; font-size: 11px; font-weight: 500;")

        cb_s = f"color: {t.text_secondary}; font-size: 10px; font-weight: 500;"
        self._random_cb.setStyleSheet(cb_s)
        self._topmost_cb.setStyleSheet(cb_s)

        self._summary.setStyleSheet(
            f"color: {t.text_secondary}; font-size: 12px; font-weight: 500;")

        self._start_btn.setStyleSheet(
            f"background-color: {t.start_bg}; color: {t.start_text}; "
            f"font-size: 14px; font-weight: 600; letter-spacing: 1px; border: none;")

    def _toggle_theme(self):
        self.theme.toggle()
        self._apply_theme()
        self._theme_btn.update()

    # ------------------------------------------------------------------ Mode

    def _set_timer_mode(self, mode):
        self._timer_mode = mode
        if mode == "standard":
            self._mode_stack.setCurrentWidget(self._standard_widget)
        else:
            self._mode_stack.setCurrentWidget(self._session_widget)
        self._update_mode_buttons()
        self._update_summary()

    def _update_mode_buttons(self):
        t = self.theme
        active_s = (f"background-color: {t.bg_active}; color: {t.text_primary}; "
                    f"border: 1px solid {t.border}; font-size: 12px; font-weight: 500; padding: 6px;")
        inactive_s = (f"background-color: {t.bg}; color: {t.text_secondary}; "
                      f"border: 1px solid {t.border}; font-size: 12px; font-weight: 500; padding: 6px;")
        if self._timer_mode == "standard":
            self._standard_btn.setStyleSheet(active_s)
            self._session_btn.setStyleSheet(inactive_s)
        else:
            self._standard_btn.setStyleSheet(inactive_s)
            self._session_btn.setStyleSheet(active_s)

    # ------------------------------------------------------------------ Standard timer

    def _select_preset_by_secs(self, secs):
        for i, (s, _) in enumerate(TIMER_PRESETS):
            if s == secs:
                self._preset_index = i
                self._update_preset_styles()
                self._update_summary()
                return

    def _update_preset_styles(self):
        t = self.theme
        current_secs = TIMER_PRESETS[self._preset_index][0]
        for btn in self._preset_buttons:
            is_active = btn._secs == current_secs
            btn.setChecked(is_active)
            if is_active:
                btn.setStyleSheet(
                    f"background-color: {t.bg_active}; color: {t.text_primary}; "
                    f"border: 1px solid {t.border_active}; font-size: 11px; font-weight: 500; padding: 5px 10px;")
            else:
                btn.setStyleSheet(
                    f"background-color: {t.bg_button}; color: {t.text_secondary}; "
                    f"border: 1px solid {t.border}; font-size: 11px; font-weight: 500; padding: 5px 10px;")

    def get_timer_seconds(self):
        return TIMER_PRESETS[self._preset_index][0]

    # ------------------------------------------------------------------ Session timer

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

    # ------------------------------------------------------------------ Tiers

    def _get_selected_tiers(self):
        tiers = []
        for btn in self._tier_toggles:
            if btn.active:
                tiers.append((btn.seconds, btn.text()))
        return tiers if tiers else None

    def _update_tier_styles(self):
        t = self.theme
        for btn in self._tier_toggles:
            if btn.isChecked():
                btn.setStyleSheet(
                    f"background-color: {t.bg_active}; color: {t.text_primary}; "
                    f"border: 1px solid {t.border_active}; font-size: 10px; font-weight: 500; padding: 3px 7px;")
            else:
                btn.setStyleSheet(
                    f"background-color: {t.bg_button}; color: {t.text_secondary}; "
                    f"border: 1px solid {t.border}; font-size: 10px; font-weight: 500; padding: 3px 7px;")

    # ------------------------------------------------------------------ Auto-distribute

    def _reset_groups(self):
        self._manual_groups = []
        self._class_groups = []
        self._update_groups_display()
        self._update_summary()

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
        self._update_groups_display()
        self._update_summary()

    def _update_groups_display(self):
        if not self._class_groups:
            self._groups_label.setText("")
            return
        parts = []
        for count, timer in self._class_groups:
            if timer >= 3600:
                t = f"{timer // 3600}ч"
            elif timer >= 60:
                t = f"{timer // 60}м"
            else:
                t = f"{timer}с"
            parts.append(f"{count}x{t}")
        self._groups_label.setText("  ".join(parts))

    # ------------------------------------------------------------------ Summary

    def _update_summary(self):
        n = len(self.images)
        if self._timer_mode == "standard":
            if n == 0:
                self._summary.setText("")
            else:
                total = n * self.get_timer_seconds()
                self._summary.setText(f"{n} изображений / {format_time(total)}")
        else:
            if n == 0:
                self._summary.setText("")
            elif self._class_groups:
                used = sum(c for c, _ in self._class_groups)
                dur = total_duration(self._class_groups)
                ses = self._get_session_seconds()
                self._summary.setText(
                    f"{used} из {n} изображений / {format_time(dur)} из {format_time(ses)}")
            else:
                self._summary.setText(f"{n} изображений")

    # ------------------------------------------------------------------ Thumbnails

    def _update_thumbnails(self):
        from PyQt6.QtGui import QPixmap
        max_thumbs = len(self._thumb_labels)
        n = len(self.images)
        show = min(n, max_thumbs)
        overflow = n - show

        for i in range(max_thumbs):
            if i < show:
                pix = QPixmap(self.images[i].path)
                if not pix.isNull():
                    pix = pix.scaled(36, 36,
                                     Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation)
                    self._thumb_labels[i].setPixmap(pix)
                else:
                    self._thumb_labels[i].setText("?")
                self._thumb_labels[i].show()
            else:
                self._thumb_labels[i].hide()
                self._thumb_labels[i].clear()

        if overflow > 0:
            self._overflow_label.setText(f"+{overflow}")
            self._overflow_label.show()
        else:
            self._overflow_label.hide()

    # ------------------------------------------------------------------ Image management

    def _add_files(self):
        exts = " ".join(f"*{e}" for e in SUPPORTED_FORMATS)
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Выберите файлы", "",
            f"Изображения ({exts});;Все файлы (*)"
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
        self._update_thumbnails()
        self._update_summary()
        self.images_changed.emit()
        if self.editor and self.editor.isVisible():
            self.editor.refresh(self.images)

    def _open_editor(self):
        from ui.image_editor_window import ImageEditorWindow
        if self.editor is None or not self.editor.isVisible():
            self.editor = ImageEditorWindow(self.images, self.theme, parent=self)
            self.editor.images_updated.connect(self._on_editor_update)
            self.editor.show()

    def _on_editor_update(self, images):
        self.images = images
        self._update_thumbnails()
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
        if self._timer_mode == "session" and self._class_groups:
            timers = groups_to_timers(self._class_groups)
            show_images = []
            for i, img in enumerate(self.images):
                if i < len(timers):
                    img.timer = timers[i]
                    show_images.append(img)

        settings = {
            "order": "random" if self._random_cb.isChecked() else "sequential",
            "topmost": self._topmost_cb.isChecked(),
        }
        from ui.viewer_window import ViewerWindow
        self.viewer = ViewerWindow(show_images, settings, on_close=self._on_viewer_closed)
        self.viewer.show()
        self.hide()

    def _on_viewer_closed(self):
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

        if data.get("timer_mode") == "class":
            self._timer_mode = "session"

        session_secs = data.get("session_seconds")
        if session_secs:
            for i, (s, _) in enumerate(SESSION_PRESETS):
                if s == session_secs:
                    self._session_index = i
                    break

        self._random_cb.setChecked(data.get("random_order", False))
        self._topmost_cb.setChecked(data.get("topmost", False))

        theme_name = data.get("theme", "dark")
        if theme_name != self.theme.name:
            self.theme.toggle()
            self._apply_theme()

        self._update_preset_styles()
        self._update_session_display()
        self._set_timer_mode(self._timer_mode)
        self._update_thumbnails()
        self._update_summary()

    def _save_session(self):
        data = {
            "images": [img.to_dict() for img in self.images],
            "timer_seconds": self.get_timer_seconds(),
            "timer_mode": "class" if self._timer_mode == "session" else "standard",
            "session_seconds": self._get_session_seconds(),
            "random_order": self._random_cb.isChecked(),
            "topmost": self._topmost_cb.isChecked(),
            "theme": self.theme.name,
        }
        save_session(data)

    # ------------------------------------------------------------------ Close

    def closeEvent(self, event):
        if self.viewer is not None and self.viewer.isVisible():
            event.ignore()
            self.hide()
        else:
            self._save_session()
            event.accept()
