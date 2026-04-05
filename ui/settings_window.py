import os
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                              QPushButton, QLabel, QComboBox, QRadioButton,
                              QCheckBox, QLineEdit, QFileDialog, QMessageBox,
                              QGroupBox, QScrollArea, QButtonGroup)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from core.constants import SUPPORTED_FORMATS, TIMER_PRESETS, SESSION_PRESETS
from core.timer_logic import validate_timer_seconds
from core.class_mode import auto_distribute, groups_to_timers, total_duration, format_group
from core.file_utils import filter_image_files, scan_folder
from core.session import save_session, load_session
from core.models import ImageItem
from ui.image_list_widget import ImageListWidget


class SettingsWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RefBot — Настройки")
        self.setMinimumWidth(480)
        self.images = []
        self.viewer = None

        self._build_ui()
        self._restore_session()
        self.setAcceptDrops(True)

    # ------------------------------------------------------------------ UI

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        root.addWidget(self._build_timer_group())
        root.addWidget(self._build_images_group())
        root.addWidget(self._build_options_group())

        self.start_btn = QPushButton("▶  Старт")
        self.start_btn.setFixedHeight(44)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #5a5aaa;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border-radius: 8px;
            }
            QPushButton:hover { background-color: #6a6abb; }
            QPushButton:pressed { background-color: #4a4a99; }
        """)
        self.start_btn.clicked.connect(self._start_slideshow)
        root.addWidget(self.start_btn)

        self.setStyleSheet("background-color: #1e1e2e; color: #cdd6f4;")

    def _build_timer_group(self):
        group = QGroupBox("Таймер")
        group.setStyleSheet(self._group_style())
        layout = QVBoxLayout(group)

        mode_row = QHBoxLayout()
        self.radio_preset = QRadioButton("Стандартный")
        self.radio_custom = QRadioButton("Настраиваемый")
        self.radio_class = QRadioButton("Сеанс")
        self.radio_preset.setChecked(True)
        self._timer_mode_group = QButtonGroup()
        self._timer_mode_group.addButton(self.radio_preset)
        self._timer_mode_group.addButton(self.radio_custom)
        self._timer_mode_group.addButton(self.radio_class)
        mode_row.addWidget(self.radio_preset)
        mode_row.addWidget(self.radio_custom)
        mode_row.addWidget(self.radio_class)
        mode_row.addStretch()
        layout.addLayout(mode_row)

        # --- Standard/Custom controls ---
        self.standard_widget = QWidget()
        std_layout = QVBoxLayout(self.standard_widget)
        std_layout.setContentsMargins(0, 0, 0, 0)

        # Preset combo
        self.preset_combo = QComboBox()
        for secs, label in TIMER_PRESETS:
            self.preset_combo.addItem(label, secs)
        self.preset_combo.addItem("Своё время...", -1)
        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        std_layout.addWidget(self.preset_combo)

        # Custom time row (hidden by default)
        self.custom_widget = QWidget()
        custom_row = QHBoxLayout(self.custom_widget)
        custom_row.setContentsMargins(0, 0, 0, 0)
        custom_row.addWidget(QLabel("Часы:"))
        self.custom_h = QLineEdit("0")
        self.custom_h.setFixedWidth(50)
        custom_row.addWidget(self.custom_h)
        custom_row.addWidget(QLabel("Мин:"))
        self.custom_m = QLineEdit("5")
        self.custom_m.setFixedWidth(50)
        custom_row.addWidget(self.custom_m)
        custom_row.addWidget(QLabel("Сек:"))
        self.custom_s = QLineEdit("0")
        self.custom_s.setFixedWidth(50)
        custom_row.addWidget(self.custom_s)
        custom_row.addStretch()
        self.custom_widget.setVisible(False)
        std_layout.addWidget(self.custom_widget)

        layout.addWidget(self.standard_widget)

        # --- Class mode controls ---
        self.class_widget = QWidget()
        class_layout = QVBoxLayout(self.class_widget)
        class_layout.setContentsMargins(0, 0, 0, 0)

        # Session duration
        dur_row = QHBoxLayout()
        dur_row.addWidget(QLabel("Длительность сеанса:"))
        self.session_combo = QComboBox()
        for secs, label in SESSION_PRESETS:
            self.session_combo.addItem(label, secs)
        self.session_combo.currentIndexChanged.connect(self._on_class_mode_changed)
        dur_row.addWidget(self.session_combo)
        dur_row.addStretch()
        class_layout.addLayout(dur_row)

        # Auto distribute button
        auto_row = QHBoxLayout()
        auto_btn = QPushButton("Авто-распределение")
        auto_btn.clicked.connect(self._auto_distribute)
        auto_row.addWidget(auto_btn)
        auto_row.addStretch()
        class_layout.addLayout(auto_row)

        # Manual group editor
        self.groups_list = QLabel("")
        self.groups_list.setStyleSheet("color: #aaa; padding: 4px;")
        self.groups_list.setWordWrap(True)
        class_layout.addWidget(self.groups_list)

        # Manual add group
        manual_row = QHBoxLayout()
        manual_row.addWidget(QLabel("Добавить:"))
        self.group_count = QLineEdit("5")
        self.group_count.setFixedWidth(40)
        manual_row.addWidget(self.group_count)
        manual_row.addWidget(QLabel("×"))
        self.group_timer_combo = QComboBox()
        for secs, label in [(30, "30 сек"), (60, "1 мин"), (120, "2 мин"),
                             (300, "5 мин"), (600, "10 мин"), (900, "15 мин")]:
            self.group_timer_combo.addItem(label, secs)
        manual_row.addWidget(self.group_timer_combo)
        add_group_btn = QPushButton("+")
        add_group_btn.setFixedWidth(30)
        add_group_btn.clicked.connect(self._add_manual_group)
        manual_row.addWidget(add_group_btn)
        clear_groups_btn = QPushButton("Сброс")
        clear_groups_btn.clicked.connect(self._clear_groups)
        manual_row.addWidget(clear_groups_btn)
        manual_row.addStretch()
        class_layout.addLayout(manual_row)

        # Total info
        self.class_info = QLabel("")
        self.class_info.setStyleSheet("color: #7a7aff;")
        class_layout.addWidget(self.class_info)

        self.class_widget.setVisible(False)
        layout.addWidget(self.class_widget)

        self._class_groups = []  # list of (count, timer_seconds)

        self.radio_preset.toggled.connect(self._on_timer_mode_changed)
        self.radio_custom.toggled.connect(self._on_timer_mode_changed)
        self.radio_class.toggled.connect(self._on_timer_mode_changed)

        return group

    def _build_images_group(self):
        group = QGroupBox("Изображения")
        group.setStyleSheet(self._group_style())
        layout = QVBoxLayout(group)

        # Top controls row
        top_row = QHBoxLayout()
        self.add_combo = QComboBox()
        self.add_combo.addItem("+ Добавить")
        self.add_combo.addItem("Файлы")
        self.add_combo.addItem("Папка")
        self.add_combo.activated.connect(lambda idx: self._on_add_selected(self.add_combo.itemText(idx)))
        top_row.addWidget(self.add_combo)

        self.up_btn = QPushButton("▲")
        self.up_btn.setFixedWidth(32)
        self.up_btn.clicked.connect(self._move_up)
        top_row.addWidget(self.up_btn)

        self.down_btn = QPushButton("▼")
        self.down_btn.setFixedWidth(32)
        self.down_btn.clicked.connect(self._move_down)
        top_row.addWidget(self.down_btn)

        self.del_btn = QPushButton("✕")
        self.del_btn.setFixedWidth(32)
        self.del_btn.clicked.connect(self._delete_selected)
        top_row.addWidget(self.del_btn)

        self.clear_btn = QPushButton("Очистить")
        self.clear_btn.clicked.connect(self._clear_images)
        top_row.addWidget(self.clear_btn)
        layout.addLayout(top_row)

        self._apply_button_style(self.up_btn)
        self._apply_button_style(self.down_btn)
        self._apply_button_style(self.del_btn)
        self._apply_button_style(self.clear_btn)

        # Image list
        self.image_list = ImageListWidget()
        self.image_list.setMinimumHeight(180)
        self.image_list.order_changed.connect(self._on_order_changed)
        layout.addWidget(self.image_list)

        # Filename checkbox
        self.show_filenames_cb = QCheckBox("Показывать имена файлов")
        self.show_filenames_cb.toggled.connect(
            lambda checked: self.image_list.set_show_filenames(checked)
        )
        layout.addWidget(self.show_filenames_cb)

        return group

    def _build_options_group(self):
        group = QGroupBox("Параметры")
        group.setStyleSheet(self._group_style())
        layout = QVBoxLayout(group)

        self.random_cb = QCheckBox("Случайный порядок")
        self.topmost_cb = QCheckBox("Поверх всех окон")
        layout.addWidget(self.random_cb)
        layout.addWidget(self.topmost_cb)

        return group

    # ------------------------------------------------------------------ Styling helpers

    def _group_style(self):
        return """
            QGroupBox {
                color: #cdd6f4;
                font-weight: bold;
                border: 1px solid #44475a;
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
            QRadioButton, QCheckBox, QLabel { color: #cdd6f4; }
            QComboBox {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #44475a;
                border-radius: 4px;
                padding: 2px 6px;
            }
            QLineEdit {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #44475a;
                border-radius: 4px;
                padding: 2px 4px;
            }
        """

    def _apply_button_style(self, btn):
        btn.setStyleSheet("""
            QPushButton {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #44475a;
                border-radius: 4px;
                padding: 2px 6px;
            }
            QPushButton:hover { background-color: #44475a; }
            QPushButton:pressed { background-color: #585b70; }
        """)

    # ------------------------------------------------------------------ Timer logic

    def _on_timer_mode_changed(self):
        is_class = self.radio_class.isChecked()
        self.standard_widget.setVisible(not is_class)
        self.class_widget.setVisible(is_class)
        if not is_class:
            is_custom = self.radio_custom.isChecked()
            self.preset_combo.setEnabled(not is_custom)
            self.custom_widget.setVisible(is_custom)

    def _on_class_mode_changed(self):
        """Auto-distribute when session duration changes."""
        if self.radio_class.isChecked() and self.images:
            self._auto_distribute()

    def _auto_distribute(self):
        """Auto-distribute images across timed groups."""
        if not self.images:
            return
        total_secs = self.session_combo.currentData()
        self._class_groups = auto_distribute(len(self.images), total_secs)
        self._update_class_display()

    def _add_manual_group(self):
        """Add a manual group to the class mode."""
        try:
            count = int(self.group_count.text() or 1)
        except ValueError:
            count = 1
        timer = self.group_timer_combo.currentData()
        if count > 0 and timer > 0:
            self._class_groups.append((count, timer))
            self._update_class_display()

    def _clear_groups(self):
        self._class_groups = []
        self._update_class_display()

    def _update_class_display(self):
        """Update the groups display and info."""
        if not self._class_groups:
            self.groups_list.setText("Нет групп")
            self.class_info.setText("")
            return
        lines = [format_group(c, t) for c, t in self._class_groups]
        self.groups_list.setText("\n".join(lines))
        total = total_duration(self._class_groups)
        total_images = sum(c for c, _ in self._class_groups)
        from core.timer_logic import format_time
        self.class_info.setText(
            f"Всего: {total_images} картинок, {format_time(total)}")

    def _on_preset_changed(self, index):
        val = self.preset_combo.itemData(index)
        self.custom_widget.setVisible(val == -1)

    def get_timer_seconds(self):
        if self.radio_custom.isChecked():
            try:
                h = int(self.custom_h.text() or 0)
                m = int(self.custom_m.text() or 0)
                s = int(self.custom_s.text() or 0)
                return validate_timer_seconds(h * 3600 + m * 60 + s)
            except ValueError:
                return 300
        else:
            val = self.preset_combo.currentData()
            if val and val > 0:
                return val
            # "Своё время..." selected but we're in preset mode — fallback
            return 300

    # ------------------------------------------------------------------ Image management

    def _on_add_selected(self, text):
        if text == "Файлы":
            self._add_files()
        elif text == "Папка":
            self._add_folder()
        sender = self.sender()
        if sender:
            sender.setCurrentIndex(0)

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
            self.image_list.set_images(self.images)

    def _add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку")
        if folder:
            timer = self.get_timer_seconds()
            for p in scan_folder(folder):
                self.images.append(ImageItem(path=p, timer=timer))
            self.image_list.set_images(self.images)

    def _move_up(self):
        self.image_list.move_current_up()
        self.images = self.image_list.get_ordered_images()

    def _move_down(self):
        self.image_list.move_current_down()
        self.images = self.image_list.get_ordered_images()

    def _delete_selected(self):
        self.image_list.delete_selected()
        self.images = self.image_list.get_ordered_images()

    def _clear_images(self):
        self.images = []
        self.image_list.set_images(self.images)

    def _on_order_changed(self):
        self.images = self.image_list.get_ordered_images()

    # ------------------------------------------------------------------ Drag and drop

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

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
            self.image_list.set_images(self.images)
        event.acceptProposedAction()

    # ------------------------------------------------------------------ Slideshow

    def _start_slideshow(self):
        if not self.images:
            return

        # Apply class mode timers if active
        if self.radio_class.isChecked() and self._class_groups:
            timers = groups_to_timers(self._class_groups)
            for i, img in enumerate(self.images):
                if i < len(timers):
                    img.timer = timers[i]
                else:
                    img.timer = timers[-1] if timers else 300

        settings = {
            "order": "random" if self.random_cb.isChecked() else "sequential",
            "topmost": self.topmost_cb.isChecked(),
        }
        from ui.viewer_window import ViewerWindow
        self.viewer = ViewerWindow(self.images, settings, on_close=self._on_viewer_closed)
        self.viewer.show()
        self.hide()

    def _on_viewer_closed(self):
        self.viewer = None
        self.show()

    # ------------------------------------------------------------------ Session

    def _restore_session(self):
        data = load_session()
        if not data:
            return
        images_data = data.get("images", [])
        self.images = [ImageItem.from_dict(d) for d in images_data]
        # Filter out missing files
        self.images = [img for img in self.images if os.path.isfile(img.path)]
        self.image_list.set_images(self.images)

        timer_secs = data.get("timer_seconds", 300)
        # Try to match a preset
        matched = False
        for i in range(self.preset_combo.count()):
            if self.preset_combo.itemData(i) == timer_secs:
                self.preset_combo.setCurrentIndex(i)
                matched = True
                break
        if not matched:
            # Set custom
            self.radio_custom.setChecked(True)
            h, rem = divmod(timer_secs, 3600)
            m, s = divmod(rem, 60)
            self.custom_h.setText(str(h))
            self.custom_m.setText(str(m))
            self.custom_s.setText(str(s))

        self.random_cb.setChecked(data.get("random_order", False))
        self.topmost_cb.setChecked(data.get("topmost", False))
        self.show_filenames_cb.setChecked(data.get("show_filenames", False))
        self.image_list.set_show_filenames(data.get("show_filenames", False))

    def _save_session(self):
        data = {
            "images": [img.to_dict() for img in self.images],
            "timer_seconds": self.get_timer_seconds(),
            "random_order": self.random_cb.isChecked(),
            "topmost": self.topmost_cb.isChecked(),
            "show_filenames": self.show_filenames_cb.isChecked(),
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
