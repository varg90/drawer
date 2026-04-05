# RefBot PyQt6 Migration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate RefBot from CustomTkinter to PyQt6 with clean core/ui separation for future Rust/C++ migration.

**Architecture:** Split into `core/` (pure Python logic, no UI deps — future Rust candidate) and `ui/` (PyQt6 widgets). Entry point `main.py` wires them together. Core owns: image list, timer logic, session persistence, file filtering. UI owns: windows, widgets, user interaction.

**Tech Stack:** Python 3.14, PyQt6, Pillow (thumbnails only)

---

## File Structure

```
C:\Users\Ellie\sandbox\
├── main.py                  # Entry point — creates QApplication, wires core + ui
├── core/
│   ├── __init__.py
│   ├── constants.py         # SUPPORTED_FORMATS, TIMER_PRESETS, TIMER_MIN/MAX
│   ├── models.py            # ImageItem dataclass, SessionData
│   ├── timer_logic.py       # validate_timer_seconds, format_time, auto_warn_seconds
│   ├── file_utils.py        # filter_image_files, scan_folder
│   └── session.py           # save_session, load_session, APP_DIR, SESSION_FILE
├── ui/
│   ├── __init__.py
│   ├── settings_window.py   # SettingsWindow (QMainWindow)
│   ├── viewer_window.py     # ViewerWindow (QWidget, frameless)
│   └── image_list_widget.py # ImageListWidget (QListWidget with drag-drop, thumbnails)
├── tests/
│   ├── test_constants.py
│   ├── test_timer_logic.py
│   ├── test_file_utils.py
│   ├── test_session.py
│   └── test_models.py
└── session.json             # auto-generated
```

Key design decisions:
- `core/` has ZERO imports from `ui/`, `PyQt6`, or any GUI library
- `ui/` imports from `core/` but core never imports from ui
- This boundary = future FFI boundary (Rust core + Python/Qt ui)
- `QListWidget` replaces custom CTkFrame rows — native drag-drop, no flicker
- `QTimer` replaces `after()` — proper event loop integration

---

### Task 1: Extract core module from existing main.py

**Files:**
- Create: `core/__init__.py`
- Create: `core/constants.py`
- Create: `core/timer_logic.py`
- Create: `core/file_utils.py`
- Create: `core/session.py`
- Create: `core/models.py`
- Modify: `tests/test_slideshow.py` → split into multiple test files

- [ ] **Step 1: Create core/constants.py**

```python
# core/constants.py
SUPPORTED_FORMATS = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp")

TIMER_PRESETS = [
    (60, "1 мин"),
    (300, "5 мин"),
    (600, "10 мин"),
    (900, "15 мин"),
    (1800, "30 мин"),
    (3600, "1 час"),
]

TIMER_MIN = 1        # 1 second
TIMER_MAX = 10800    # 3 hours
```

- [ ] **Step 2: Create core/timer_logic.py**

```python
# core/timer_logic.py
from core.constants import TIMER_MIN, TIMER_MAX


def validate_timer_seconds(seconds):
    """Clamp timer value to valid range."""
    return max(TIMER_MIN, min(TIMER_MAX, int(seconds)))


def format_time(s):
    """Format seconds into human-readable time string."""
    if s >= 3600:
        return f"{s // 3600}:{(s % 3600) // 60:02d}:{s % 60:02d}"
    elif s >= 60:
        return f"{s // 60}:{s % 60:02d}"
    else:
        return f"0:{s:02d}"


def auto_warn_seconds(timer_seconds):
    """Calculate warning time based on timer duration."""
    if timer_seconds <= 120:
        return 10
    elif timer_seconds <= 300:
        return 30
    elif timer_seconds <= 900:
        return 60
    elif timer_seconds <= 3600:
        return 300
    else:
        return 600
```

- [ ] **Step 3: Create core/file_utils.py**

```python
# core/file_utils.py
import os
from core.constants import SUPPORTED_FORMATS


def filter_image_files(file_paths):
    """Return only files with supported image extensions."""
    return [f for f in file_paths if os.path.splitext(f)[1].lower() in SUPPORTED_FORMATS]


def scan_folder(folder_path):
    """Return all image files in a folder."""
    all_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path)]
    return filter_image_files(all_files)
```

- [ ] **Step 4: Create core/models.py**

```python
# core/models.py
from dataclasses import dataclass, field


@dataclass
class ImageItem:
    path: str
    timer: int = 300  # seconds

    def to_dict(self):
        return {"path": self.path, "timer": self.timer}

    @classmethod
    def from_dict(cls, d):
        return cls(path=d["path"], timer=d.get("timer", 300))
```

- [ ] **Step 5: Create core/session.py**

```python
# core/session.py
import os
import sys
import json

if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SESSION_FILE = os.path.join(APP_DIR, "session.json")


def save_session(data, path=None):
    """Save session data to JSON file."""
    if path is None:
        path = SESSION_FILE
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_session(path=None):
    """Load session data from JSON file. Returns None if file missing or corrupted."""
    if path is None:
        path = SESSION_FILE
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None
```

- [ ] **Step 6: Create core/__init__.py**

```python
# core/__init__.py
```

- [ ] **Step 7: Split tests into separate files**

Create `tests/test_constants.py`:
```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.constants import SUPPORTED_FORMATS, TIMER_PRESETS, TIMER_MIN, TIMER_MAX


def test_supported_formats():
    assert ".jpg" in SUPPORTED_FORMATS
    assert ".txt" not in SUPPORTED_FORMATS

def test_timer_presets():
    assert len(TIMER_PRESETS) == 6
    assert [s for s, _ in TIMER_PRESETS] == [60, 300, 600, 900, 1800, 3600]

def test_timer_range():
    assert TIMER_MIN == 1
    assert TIMER_MAX == 10800
```

Create `tests/test_timer_logic.py`:
```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.timer_logic import validate_timer_seconds, format_time, auto_warn_seconds


def test_validate_timer_valid():
    assert validate_timer_seconds(1) == 1
    assert validate_timer_seconds(60) == 60
    assert validate_timer_seconds(10800) == 10800

def test_validate_timer_clamps_low():
    assert validate_timer_seconds(0) == 1
    assert validate_timer_seconds(-5) == 1

def test_validate_timer_clamps_high():
    assert validate_timer_seconds(10801) == 10800
    assert validate_timer_seconds(99999) == 10800

def test_validate_timer_float():
    assert validate_timer_seconds(5.7) == 5

def test_validate_timer_boundary():
    assert validate_timer_seconds(1) == 1
    assert validate_timer_seconds(10800) == 10800

def test_format_time_seconds():
    assert format_time(0) == "0:00"
    assert format_time(1) == "0:01"
    assert format_time(59) == "0:59"

def test_format_time_minutes():
    assert format_time(60) == "1:00"
    assert format_time(90) == "1:30"
    assert format_time(3599) == "59:59"

def test_format_time_hours():
    assert format_time(3600) == "1:00:00"
    assert format_time(3661) == "1:01:01"
    assert format_time(10800) == "3:00:00"

def test_auto_warn_up_to_2min():
    assert auto_warn_seconds(1) == 10
    assert auto_warn_seconds(120) == 10

def test_auto_warn_2min_to_5min():
    assert auto_warn_seconds(121) == 30
    assert auto_warn_seconds(300) == 30

def test_auto_warn_5min_to_15min():
    assert auto_warn_seconds(301) == 60
    assert auto_warn_seconds(900) == 60

def test_auto_warn_15min_to_1hour():
    assert auto_warn_seconds(901) == 300
    assert auto_warn_seconds(3600) == 300

def test_auto_warn_1hour_to_3hours():
    assert auto_warn_seconds(3601) == 600
    assert auto_warn_seconds(10800) == 600

def test_auto_warn_boundaries():
    assert auto_warn_seconds(120) == 10
    assert auto_warn_seconds(121) == 30
    assert auto_warn_seconds(300) == 30
    assert auto_warn_seconds(301) == 60
    assert auto_warn_seconds(900) == 60
    assert auto_warn_seconds(901) == 300
    assert auto_warn_seconds(3600) == 300
    assert auto_warn_seconds(3601) == 600
```

Create `tests/test_file_utils.py`:
```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.file_utils import filter_image_files


def test_filter_mixed():
    files = ["photo.jpg", "image.PNG", "doc.txt", "art.webp", "data.csv", "pic.gif", "shot.bmp", "render.jpeg"]
    result = filter_image_files(files)
    assert result == ["photo.jpg", "image.PNG", "art.webp", "pic.gif", "shot.bmp", "render.jpeg"]

def test_filter_empty():
    assert filter_image_files([]) == []
    assert filter_image_files(["readme.txt"]) == []

def test_filter_all_images():
    assert filter_image_files(["a.jpg", "b.png"]) == ["a.jpg", "b.png"]

def test_filter_case_insensitive():
    assert filter_image_files(["A.JPG", "B.Png"]) == ["A.JPG", "B.Png"]

def test_filter_with_paths():
    files = ["C:/photos/beach.jpg", "C:/docs/report.pdf", "/home/user/art.webp"]
    assert filter_image_files(files) == ["C:/photos/beach.jpg", "/home/user/art.webp"]

def test_filter_no_extension():
    assert filter_image_files(["README", "Makefile"]) == []

def test_filter_double_extension():
    assert filter_image_files(["photo.backup.jpg", "doc.txt.png"]) == ["photo.backup.jpg", "doc.txt.png"]
```

Create `tests/test_session.py`:
```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import tempfile
from core.session import save_session, load_session


def test_save_and_load():
    data = {"images": [{"path": "C:/a.jpg", "timer": 60}], "order": "sequential"}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        path = f.name
    save_session(data, path)
    assert load_session(path) == data
    os.unlink(path)

def test_load_missing():
    assert load_session("nonexistent_12345.json") is None

def test_load_corrupted():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("not json{{{")
        path = f.name
    assert load_session(path) is None
    os.unlink(path)

def test_save_unicode():
    data = {"name": "Оксана", "path": "C:/фото/картинка.jpg"}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        path = f.name
    save_session(data, path)
    assert load_session(path) == data
    os.unlink(path)

def test_save_empty():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        path = f.name
    save_session({}, path)
    assert load_session(path) == {}
    os.unlink(path)

def test_save_overwrites():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        path = f.name
    save_session({"v": 1}, path)
    save_session({"v": 2}, path)
    assert load_session(path) == {"v": 2}
    os.unlink(path)

def test_load_empty_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        path = f.name
    assert load_session(path) is None
    os.unlink(path)

def test_save_large_list():
    data = {"images": [{"path": f"C:/img/{i}.jpg", "timer": 60} for i in range(1000)]}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        path = f.name
    save_session(data, path)
    assert len(load_session(path)["images"]) == 1000
    os.unlink(path)
```

Create `tests/test_models.py`:
```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.models import ImageItem


def test_image_item_defaults():
    item = ImageItem(path="C:/a.jpg")
    assert item.path == "C:/a.jpg"
    assert item.timer == 300

def test_image_item_custom_timer():
    item = ImageItem(path="C:/a.jpg", timer=60)
    assert item.timer == 60

def test_image_item_to_dict():
    item = ImageItem(path="C:/a.jpg", timer=120)
    assert item.to_dict() == {"path": "C:/a.jpg", "timer": 120}

def test_image_item_from_dict():
    item = ImageItem.from_dict({"path": "C:/b.png", "timer": 600})
    assert item.path == "C:/b.png"
    assert item.timer == 600

def test_image_item_from_dict_default_timer():
    item = ImageItem.from_dict({"path": "C:/c.gif"})
    assert item.timer == 300

def test_image_item_roundtrip():
    original = ImageItem(path="C:/test.webp", timer=42)
    restored = ImageItem.from_dict(original.to_dict())
    assert original == restored
```

- [ ] **Step 8: Run all tests**

Run: `python -m pytest tests/ -v`
Expected: All pass (same coverage as before, split across files)

- [ ] **Step 9: Commit**

```bash
git add core/ tests/
git commit -m "refactor: extract core module with clean separation from UI"
```

---

### Task 2: Settings window in PyQt6

**Files:**
- Create: `ui/__init__.py`
- Create: `ui/image_list_widget.py`
- Create: `ui/settings_window.py`

- [ ] **Step 1: Create ui/__init__.py**

```python
# ui/__init__.py
```

- [ ] **Step 2: Create ui/image_list_widget.py**

```python
# ui/image_list_widget.py
import os
from PyQt6.QtWidgets import (QListWidget, QListWidgetItem, QWidget, QHBoxLayout,
                              QLabel, QPushButton, QCheckBox)
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import Qt, pyqtSignal, QSize


class ImageListWidget(QListWidget):
    """Image list with thumbnails, reordering, and drag-drop."""
    order_changed = pyqtSignal()
    selection_changed = pyqtSignal(int)  # emits index

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.setStyleSheet("""
            QListWidget { background-color: #2b2b3d; border: none; border-radius: 6px; }
            QListWidget::item { padding: 4px; }
            QListWidget::item:selected { background-color: #3a3a6a; }
        """)
        self.setIconSize(QSize(48, 48))
        self.model().rowsMoved.connect(lambda: self.order_changed.emit())
        self.currentRowChanged.connect(lambda row: self.selection_changed.emit(row))
        self._show_filenames = False
        self._images = []  # list of ImageItem

    def set_images(self, images):
        """Rebuild list from ImageItem list."""
        self._images = images
        self._rebuild()

    def set_show_filenames(self, show):
        self._show_filenames = show
        self._rebuild()

    def _rebuild(self):
        self.clear()
        for i, img in enumerate(self._images):
            text = ""
            if self._show_filenames:
                text = f"{i+1}. {os.path.basename(img.path)}"
            else:
                text = f"{i+1}."

            item = QListWidgetItem(text)
            # Thumbnail
            pix = QPixmap(img.path)
            if not pix.isNull():
                pix = pix.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio,
                                  Qt.TransformationMode.SmoothTransformation)
                item.setIcon(QIcon(pix))

            # Timer text
            secs = img.timer
            if secs >= 3600:
                t = f"{secs//3600}ч {(secs%3600)//60}мин"
            elif secs >= 60:
                t = f"{secs//60} мин"
            else:
                t = f"{secs} сек"
            item.setToolTip(f"Таймер: {t}")
            item.setData(Qt.ItemDataRole.UserRole, i)
            self.addItem(item)

    def get_ordered_images(self):
        """Return images in current visual order (after drag-drop reorder)."""
        result = []
        for i in range(self.count()):
            item = self.item(i)
            if item:
                orig_idx = item.data(Qt.ItemDataRole.UserRole)
                if orig_idx is not None and orig_idx < len(self._images):
                    result.append(self._images[orig_idx])
        return result if result else self._images

    def move_current_up(self):
        row = self.currentRow()
        if row > 0:
            self._images[row], self._images[row-1] = self._images[row-1], self._images[row]
            self._rebuild()
            self.setCurrentRow(row - 1)

    def move_current_down(self):
        row = self.currentRow()
        if row < len(self._images) - 1:
            self._images[row], self._images[row+1] = self._images[row+1], self._images[row]
            self._rebuild()
            self.setCurrentRow(row + 1)

    def delete_current(self):
        row = self.currentRow()
        if 0 <= row < len(self._images):
            self._images.pop(row)
            self._rebuild()
            if self._images:
                self.setCurrentRow(min(row, len(self._images) - 1))
```

- [ ] **Step 3: Create ui/settings_window.py**

```python
# ui/settings_window.py
import os
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                              QPushButton, QLabel, QComboBox, QRadioButton,
                              QCheckBox, QLineEdit, QFileDialog, QMessageBox,
                              QGroupBox, QScrollArea, QButtonGroup, QSizePolicy)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDragEnterEvent, QDropEvent

from core.constants import SUPPORTED_FORMATS, TIMER_PRESETS
from core.timer_logic import validate_timer_seconds
from core.file_utils import filter_image_files, scan_folder
from core.session import save_session, load_session
from core.models import ImageItem
from ui.image_list_widget import ImageListWidget


class SettingsWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RefBot — Настройки")
        self.setMinimumSize(400, 500)
        self.resize(500, 700)

        self.images = []  # list of ImageItem
        self.viewer = None

        # Enable drag-and-drop files onto the window
        self.setAcceptDrops(True)

        self._build_ui()
        self._check_restore_session()

    def _build_ui(self):
        # Main layout with scroll area
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        content = QWidget()
        self.content_layout = QVBoxLayout(content)
        scroll.setWidget(content)
        main_layout.addWidget(scroll, 1)

        # --- Timer section ---
        timer_group = QGroupBox("Таймер")
        timer_layout = QVBoxLayout(timer_group)

        # Timer mode
        mode_layout = QHBoxLayout()
        self.mode_group = QButtonGroup(self)
        self.uniform_radio = QRadioButton("Стандартный")
        self.individual_radio = QRadioButton("Настраиваемый")
        self.uniform_radio.setChecked(True)
        self.mode_group.addButton(self.uniform_radio)
        self.mode_group.addButton(self.individual_radio)
        mode_layout.addWidget(self.uniform_radio)
        mode_layout.addWidget(self.individual_radio)
        mode_layout.addStretch()
        timer_layout.addLayout(mode_layout)

        # Preset combo
        preset_layout = QHBoxLayout()
        self.preset_combo = QComboBox()
        for _, label in TIMER_PRESETS:
            self.preset_combo.addItem(label)
        self.preset_combo.addItem("Своё время...")
        self.preset_combo.setCurrentIndex(1)  # 5 min default
        self.preset_combo.currentTextChanged.connect(self._on_preset_changed)
        preset_layout.addWidget(self.preset_combo)
        preset_layout.addStretch()
        timer_layout.addLayout(preset_layout)

        # Custom time row (hidden by default)
        self.custom_widget = QWidget()
        custom_layout = QHBoxLayout(self.custom_widget)
        custom_layout.setContentsMargins(0, 0, 0, 0)
        self.hours_edit = QLineEdit("0")
        self.hours_edit.setFixedWidth(45)
        self.hours_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mins_edit = QLineEdit("5")
        self.mins_edit.setFixedWidth(45)
        self.mins_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.secs_edit = QLineEdit("0")
        self.secs_edit.setFixedWidth(45)
        self.secs_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ok_btn = QPushButton("OK")
        ok_btn.setFixedWidth(40)
        ok_btn.clicked.connect(self._apply_custom_timer)
        custom_layout.addWidget(self.hours_edit)
        custom_layout.addWidget(QLabel("ч"))
        custom_layout.addWidget(self.mins_edit)
        custom_layout.addWidget(QLabel("мин"))
        custom_layout.addWidget(self.secs_edit)
        custom_layout.addWidget(QLabel("сек"))
        custom_layout.addWidget(ok_btn)
        custom_layout.addWidget(QLabel("(1сек — 3ч)"))
        custom_layout.addStretch()
        self.custom_widget.hide()
        timer_layout.addWidget(self.custom_widget)

        self.content_layout.addWidget(timer_group)

        # --- Image list section ---
        img_group = QGroupBox("Картинки")
        img_layout = QVBoxLayout(img_group)

        # Buttons row
        btn_layout = QHBoxLayout()
        add_combo = QComboBox()
        add_combo.addItems(["Добавить...", "Файлы", "Папка"])
        add_combo.currentTextChanged.connect(self._on_add_selected)
        btn_layout.addWidget(add_combo)

        up_btn = QPushButton("▲")
        up_btn.setFixedWidth(30)
        up_btn.clicked.connect(lambda: self.image_list.move_current_up())
        down_btn = QPushButton("▼")
        down_btn.setFixedWidth(30)
        down_btn.clicked.connect(lambda: self.image_list.move_current_down())
        del_btn = QPushButton("✕")
        del_btn.setFixedWidth(30)
        del_btn.clicked.connect(lambda: self.image_list.delete_current())
        clear_btn = QPushButton("Очистить")
        clear_btn.clicked.connect(self._clear_images)

        btn_layout.addWidget(up_btn)
        btn_layout.addWidget(down_btn)
        btn_layout.addWidget(del_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(clear_btn)
        img_layout.addLayout(btn_layout)

        # Image list widget
        self.image_list = ImageListWidget()
        self.image_list.setMinimumHeight(150)
        img_layout.addWidget(self.image_list)

        # Show filename checkbox
        self.show_filename_cb = QCheckBox("Имя файла")
        self.show_filename_cb.toggled.connect(
            lambda checked: self.image_list.set_show_filenames(checked))
        img_layout.addWidget(self.show_filename_cb)

        self.content_layout.addWidget(img_group)

        # --- Options ---
        options_group = QGroupBox("Опции")
        options_layout = QVBoxLayout(options_group)

        self.random_cb = QCheckBox("Случайный порядок")
        self.topmost_cb = QCheckBox("Поверх всех окон")
        options_layout.addWidget(self.random_cb)
        options_layout.addWidget(self.topmost_cb)

        self.content_layout.addWidget(options_group)
        self.content_layout.addStretch()

        # --- Start button (fixed at bottom) ---
        start_btn = QPushButton("▶  Старт")
        start_btn.setFixedHeight(40)
        start_btn.setStyleSheet("font-size: 16px; font-weight: bold;")
        start_btn.clicked.connect(self._start_slideshow)
        main_layout.addWidget(start_btn)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        existing = {img.path for img in self.images}
        added = False
        for url in urls:
            p = url.toLocalFile()
            if os.path.isdir(p):
                for img_path in scan_folder(p):
                    if img_path not in existing:
                        self.images.append(ImageItem(path=img_path))
                        existing.add(img_path)
                        added = True
            elif os.path.isfile(p) and os.path.splitext(p)[1].lower() in SUPPORTED_FORMATS:
                if p not in existing:
                    self.images.append(ImageItem(path=p))
                    existing.add(p)
                    added = True
        if added:
            self.image_list.set_images(self.images)

    def _on_preset_changed(self, text):
        if text == "Своё время...":
            self.custom_widget.show()
        else:
            self.custom_widget.hide()
            preset_map = {label: secs for secs, label in TIMER_PRESETS}
            seconds = preset_map.get(text)
            if seconds is not None:
                self._set_timer(seconds)

    def _apply_custom_timer(self):
        try:
            h = int(self.hours_edit.text() or 0)
            m = int(self.mins_edit.text() or 0)
            s = int(self.secs_edit.text() or 0)
        except ValueError:
            return
        self._set_timer(h * 3600 + m * 60 + s)

    def _set_timer(self, seconds):
        seconds = validate_timer_seconds(seconds)
        if self.uniform_radio.isChecked():
            for img in self.images:
                img.timer = seconds
        else:
            row = self.image_list.currentRow()
            if 0 <= row < len(self.images):
                self.images[row].timer = seconds
        self.image_list.set_images(self.images)

    def _on_add_selected(self, text):
        if text == "Файлы":
            self._add_files()
        elif text == "Папка":
            self._add_folder()
        # Reset combo to placeholder
        sender = self.sender()
        if sender:
            sender.setCurrentIndex(0)

    def _add_files(self):
        exts = " ".join(f"*{e}" for e in SUPPORTED_FORMATS)
        paths, _ = QFileDialog.getOpenFileNames(self, "Выбери картинки", "", f"Images ({exts})")
        if not paths:
            return
        existing = {img.path for img in self.images}
        for p in filter_image_files(paths):
            if p not in existing:
                self.images.append(ImageItem(path=p))
                existing.add(p)
        self.image_list.set_images(self.images)

    def _add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выбери папку с картинками")
        if not folder:
            return
        existing = {img.path for img in self.images}
        for p in scan_folder(folder):
            if p not in existing:
                self.images.append(ImageItem(path=p))
                existing.add(p)
        self.image_list.set_images(self.images)

    def _clear_images(self):
        self.images.clear()
        self.image_list.set_images(self.images)

    def _start_slideshow(self):
        if not self.images:
            return
        settings = {
            "order": "random" if self.random_cb.isChecked() else "sequential",
            "topmost": self.topmost_cb.isChecked(),
        }
        from ui.viewer_window import ViewerWindow
        self.viewer = ViewerWindow(self.images, settings, on_close=self._on_viewer_closed)
        self.viewer.show()
        self.hide()

    def _on_viewer_closed(self):
        self.show()

    def _get_session_data(self):
        return {
            "images": [img.to_dict() for img in self.images],
            "timer_mode": "individual" if self.individual_radio.isChecked() else "uniform",
            "order": "random" if self.random_cb.isChecked() else "sequential",
            "topmost": self.topmost_cb.isChecked(),
            "show_filename": self.show_filename_cb.isChecked(),
            "window_x": self.x(),
            "window_y": self.y(),
            "window_w": self.width(),
            "window_h": self.height(),
        }

    def _apply_session(self, data):
        self.images = [ImageItem.from_dict(d) for d in data.get("images", [])
                       if os.path.exists(d.get("path", ""))]
        self.image_list.set_images(self.images)
        if data.get("timer_mode") == "individual":
            self.individual_radio.setChecked(True)
        if data.get("order") == "random":
            self.random_cb.setChecked(True)
        self.topmost_cb.setChecked(data.get("topmost", False))
        self.show_filename_cb.setChecked(data.get("show_filename", False))
        x, y = data.get("window_x", 100), data.get("window_y", 100)
        w, h = data.get("window_w", 500), data.get("window_h", 700)
        self.setGeometry(x, y, w, h)

    def _check_restore_session(self):
        data = load_session()
        if data is None:
            return
        reply = QMessageBox.question(
            self, "Восстановить сессию?", "Восстановить прошлую сессию?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._apply_session(data)

    def closeEvent(self, event):
        save_session(self._get_session_data())
        if self.viewer and self.viewer.isVisible():
            event.ignore()
            self.hide()
        else:
            event.accept()
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/ -v`
Expected: All core tests pass (UI not tested with unit tests)

- [ ] **Step 5: Commit**

```bash
git add ui/
git commit -m "feat: add PyQt6 settings window with image list and drag-drop"
```

---

### Task 3: Viewer window in PyQt6

**Files:**
- Create: `ui/viewer_window.py`

- [ ] **Step 1: Create ui/viewer_window.py**

```python
# ui/viewer_window.py
import random
from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QPushButton, QVBoxLayout
from PyQt6.QtGui import QPixmap, QPainter, QCursor
from PyQt6.QtCore import Qt, QTimer, QPoint, QSize

from core.timer_logic import format_time, auto_warn_seconds


class ViewerWindow(QWidget):
    def __init__(self, images, settings, on_close=None):
        super().__init__()
        self.setWindowTitle("RefBot")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setStyleSheet("background-color: black;")
        self.resize(800, 600)

        self.all_images = images
        self.settings = settings
        self._on_close_callback = on_close
        self.is_playing = True
        self.current_aspect = None

        # Always-on-top
        if self.settings.get("topmost"):
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

        # Play order
        self.play_order = list(range(len(self.all_images)))
        if self.settings.get("order") == "random":
            random.shuffle(self.play_order)
        self.order_position = 0

        # Image label
        self._pixmap = None
        self._image_label = QLabel(self)
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setStyleSheet("background-color: black;")

        # Controls (hidden, shown on hover)
        self._controls = QWidget(self)
        self._controls.setStyleSheet(
            "background-color: rgba(0,0,0,180); border-radius: 15px;")
        self._controls.hide()
        ctrl_layout = QHBoxLayout(self._controls)
        ctrl_layout.setContentsMargins(10, 5, 10, 5)

        btn_style = "color: white; background: transparent; border: none; font-size: 18px; padding: 5px 10px;"
        btn_hover = "QPushButton:hover { background-color: #444; border-radius: 5px; }"

        for text, callback in [
            ("⏮", self._prev), ("⏸", self._toggle_pause), ("⏭", self._next),
            ("⚙", self._open_settings), ("✕", self.close)
        ]:
            btn = QPushButton(text)
            btn.setStyleSheet(btn_style + btn_hover)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.clicked.connect(callback)
            ctrl_layout.addWidget(btn)
            if text == "⏸":
                self._pause_btn = btn

        # Timer label in controls
        self._timer_label = QLabel("")
        self._timer_label.setStyleSheet("color: #aaa; font-size: 14px;")
        ctrl_layout.insertWidget(3, self._timer_label)  # after ⏭

        # Counter label
        self._counter = QLabel(self)
        self._counter.setStyleSheet(
            "color: rgba(255,255,255,150); font-size: 12px; background: transparent;")
        self._counter.hide()

        # Warning label
        self._warn_label = QLabel(self)
        self._warn_label.setStyleSheet(
            "color: #ff3333; font-weight: bold; background: transparent;")
        self._warn_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._warn_label.hide()

        # Countdown timer
        self._countdown_remaining = 0
        self._countdown_timer = QTimer(self)
        self._countdown_timer.setInterval(1000)
        self._countdown_timer.timeout.connect(self._tick)

        # Resize grip
        self._resize_grip_size = 50
        self._resizing = False
        self._resize_corner = None
        self._resize_start_pos = QPoint()
        self._resize_start_geo = None

        # Drag to move
        self._drag_pos = None

        self.setMouseTracking(True)
        self._image_label.setMouseTracking(True)

        # Show first image
        self._show_current_image()
        self._schedule_next()

    def _show_current_image(self):
        if not self.all_images:
            return
        idx = self.play_order[self.order_position]
        path = self.all_images[idx].path
        pix = QPixmap(path)
        if pix.isNull():
            self._next()
            return

        self._pixmap = pix
        self.current_aspect = pix.width() / pix.height()

        # Fit window to image
        h = self.height()
        new_w = int(h * self.current_aspect)
        self.resize(new_w, h)

        self._update_display()
        total = len(self.all_images)
        self._counter.setText(f"{self.order_position + 1} / {total}")

    def _update_display(self):
        if self._pixmap is None:
            return
        scaled = self._pixmap.scaled(
            self.size(), Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation)
        self._image_label.setPixmap(scaled)
        self._image_label.resize(self.size())

    def _schedule_next(self):
        self._countdown_timer.stop()
        if not self.is_playing:
            self._update_timer_display()
            return
        idx = self.play_order[self.order_position]
        self._countdown_remaining = self.all_images[idx].timer
        self._update_timer_display()
        self._countdown_timer.start()

    def _tick(self):
        self._countdown_remaining -= 1
        self._update_timer_display()
        if self._countdown_remaining <= 0:
            self._countdown_timer.stop()
            self._advance()

    def _update_timer_display(self):
        s = self._countdown_remaining
        idx = self.play_order[self.order_position]
        total_timer = self.all_images[idx].timer
        warn_secs = auto_warn_seconds(total_timer)
        is_warning = self.is_playing and s <= warn_secs

        if not self.is_playing:
            self._timer_label.setText("⏸")
            self._timer_label.setStyleSheet("color: #aaa; font-size: 14px;")
        else:
            color = "#ff3333" if is_warning else "#aaa"
            self._timer_label.setText(format_time(s))
            self._timer_label.setStyleSheet(f"color: {color}; font-size: 14px;")

        # Warning overlay
        if is_warning:
            font_size = max(16, min(48, int(min(self.width(), self.height()) * 0.08)))
            self._warn_label.setStyleSheet(
                f"color: #ff3333; font-weight: bold; font-size: {font_size}px; background: transparent;")
            self._warn_label.setText(format_time(s))
            self._warn_label.adjustSize()
            self._warn_label.move(
                (self.width() - self._warn_label.width()) // 2,
                self.height() - self._warn_label.height() - 20)
            self._warn_label.show()
        else:
            self._warn_label.hide()

    def _advance(self):
        self.order_position += 1
        if self.order_position >= len(self.play_order):
            self.close()
            return
        self._show_current_image()
        self._schedule_next()

    def _next(self):
        self.order_position = (self.order_position + 1) % len(self.play_order)
        self._show_current_image()
        if self.is_playing:
            self._schedule_next()

    def _prev(self):
        self.order_position = (self.order_position - 1) % len(self.play_order)
        self._show_current_image()
        if self.is_playing:
            self._schedule_next()

    def _toggle_pause(self):
        self.is_playing = not self.is_playing
        self._pause_btn.setText("⏸" if self.is_playing else "▶")
        if self.is_playing:
            self._schedule_next()
        else:
            self._countdown_timer.stop()
            self._update_timer_display()

    def _open_settings(self):
        if self._on_close_callback:
            self._on_close_callback()

    def closeEvent(self, event):
        self._countdown_timer.stop()
        if self._on_close_callback:
            self._on_close_callback()
        event.accept()

    # --- Hover controls ---
    def enterEvent(self, event):
        self._controls.show()
        self._counter.show()

    def leaveEvent(self, event):
        self._controls.hide()
        self._counter.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._image_label.resize(self.size())
        # Center controls at bottom
        cw = self._controls.sizeHint().width()
        ch = self._controls.sizeHint().height()
        self._controls.move((self.width() - cw) // 2, self.height() - ch - 15)
        # Counter top-right
        self._counter.adjustSize()
        self._counter.move(self.width() - self._counter.width() - 10, 10)
        self._update_display()

    # --- Borderless window: resize from corners + right-click drag ---
    def _get_corner(self, pos):
        g = self._resize_grip_size
        w, h = self.width(), self.height()
        left, right = pos.x() < g, pos.x() >= w - g
        top, bottom = pos.y() < g, pos.y() >= h - g
        if top and left: return "tl"
        if top and right: return "tr"
        if bottom and left: return "bl"
        if bottom and right: return "br"
        return None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self._drag_pos = event.globalPosition().toPoint() - self.pos()
        elif event.button() == Qt.MouseButton.LeftButton:
            corner = self._get_corner(event.pos())
            if corner:
                self._resizing = True
                self._resize_corner = corner
                self._resize_start_pos = event.globalPosition().toPoint()
                self._resize_start_geo = self.geometry()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.MouseButton.RightButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
        elif self._resizing and event.buttons() & Qt.MouseButton.LeftButton:
            delta = event.globalPosition().toPoint() - self._resize_start_pos
            geo = self._resize_start_geo
            c = self._resize_corner
            x, y, w, h = geo.x(), geo.y(), geo.width(), geo.height()
            if c == "br":
                w += delta.x(); h += delta.y()
            elif c == "bl":
                x += delta.x(); w -= delta.x(); h += delta.y()
            elif c == "tr":
                y += delta.y(); w += delta.x(); h -= delta.y()
            elif c == "tl":
                x += delta.x(); y += delta.y(); w -= delta.x(); h -= delta.y()
            w = max(200, w); h = max(150, h)
            # Lock aspect ratio
            if self.current_aspect:
                target_h = int(w / self.current_aspect)
                if target_h >= h:
                    if c in ("tl", "tr"): y -= (target_h - h)
                    h = target_h
                else:
                    target_w = int(h * self.current_aspect)
                    if c in ("tl", "bl"): x -= (target_w - w)
                    w = target_w
            self.setGeometry(x, y, w, h)
        else:
            corner = self._get_corner(event.pos())
            if corner in ("tl", "br"):
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif corner in ("tr", "bl"):
                self.setCursor(Qt.CursorShape.SizeBDiagCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        if self._resizing:
            self._resizing = False
            self._update_display()
```

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests/ -v`
Expected: All core tests pass

- [ ] **Step 3: Commit**

```bash
git add ui/viewer_window.py
git commit -m "feat: add PyQt6 viewer window with borderless display and hover controls"
```

---

### Task 4: New entry point and cleanup

**Files:**
- Modify: `main.py` — replace with PyQt6 entry point
- Keep: old `main.py` as `main_ctk.py` backup

- [ ] **Step 1: Rename old main.py**

```bash
mv main.py main_ctk.py
```

- [ ] **Step 2: Create new main.py**

```python
# main.py
import sys
import os
import logging

# Resolve app directory
if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

# Logging
LOG_FILE = os.path.join(APP_DIR, "app.log")
logging.basicConfig(
    filename=LOG_FILE, level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S", encoding="utf-8"
)
log = logging.getLogger("refbot")

from PyQt6.QtWidgets import QApplication
from ui.settings_window import SettingsWindow

if __name__ == "__main__":
    log.info("App started")
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Dark palette
    from PyQt6.QtGui import QPalette, QColor
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(43, 43, 61))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(224, 224, 224))
    palette.setColor(QPalette.ColorRole.Base, QColor(30, 30, 48))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(43, 43, 61))
    palette.setColor(QPalette.ColorRole.Text, QColor(224, 224, 224))
    palette.setColor(QPalette.ColorRole.Button, QColor(60, 60, 80))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(224, 224, 224))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(90, 90, 180))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)

    window = SettingsWindow()
    window.show()
    sys.exit(app.exec())
```

- [ ] **Step 3: Run tests**

Run: `python -m pytest tests/ -v`
Expected: All pass

- [ ] **Step 4: Test the app manually**

Run: `python main.py`
Expected: Dark-themed settings window opens. Can add images, configure timer, start slideshow.

- [ ] **Step 5: Commit**

```bash
git add main.py main_ctk.py
git commit -m "feat: new PyQt6 entry point with dark theme, keep CTk backup"
```

---

### Task 5: Build exe and final cleanup

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Build exe**

Run: `python -m PyInstaller --onefile --windowed --name "RefBot" --clean main.py`
Expected: `dist/RefBot.exe` created

- [ ] **Step 2: Test exe**

Run: `dist/RefBot.exe`
Expected: App launches, session saves next to exe

- [ ] **Step 3: Run all tests one final time**

Run: `python -m pytest tests/ -v`
Expected: All pass

- [ ] **Step 4: Delete old test file**

```bash
rm tests/test_slideshow.py
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: complete PyQt6 migration — no flicker, native drag-drop, clean core/ui split"
git push
```
