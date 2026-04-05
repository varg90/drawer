# Image Slideshow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a desktop image slideshow app with configurable timers, always-on-top mode, drag-and-drop reordering, and session persistence.

**Architecture:** Single-file Python app (`main.py`) using CustomTkinter for UI and Pillow for image handling. Two windows: a viewer for displaying images and a settings panel for configuration. Session state saved to `session.json`.

**Tech Stack:** Python 3.14, CustomTkinter, Pillow, tkinter (file dialogs), JSON (session persistence)

---

## File Structure

- `main.py` — all application code (entry point, settings window, viewer window, session logic)
- `session.json` — auto-generated session file (not committed)
- `tests/test_slideshow.py` — unit tests for non-GUI logic (timer validation, session save/load, file filtering)

---

### Task 1: Install Pillow and scaffold empty app

**Files:**
- Create: `main.py`
- Create: `tests/test_slideshow.py`

- [ ] **Step 1: Install Pillow**

Run: `python -m pip install Pillow`
Expected: Successfully installed Pillow

- [ ] **Step 2: Write a test that imports the app module**

```python
# tests/test_slideshow.py
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_import():
    import main
    assert hasattr(main, "SUPPORTED_FORMATS")
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_slideshow.py::test_import -v`
Expected: FAIL — ModuleNotFoundError or AttributeError

- [ ] **Step 4: Create minimal main.py**

```python
# main.py
import customtkinter as ctk

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

if __name__ == "__main__":
    pass
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_slideshow.py::test_import -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add main.py tests/test_slideshow.py
git commit -m "feat: scaffold app with constants and Pillow dependency"
```

---

### Task 2: Timer validation and file filtering logic

**Files:**
- Modify: `main.py`
- Modify: `tests/test_slideshow.py`

- [ ] **Step 1: Write failing tests for validation functions**

Add to `tests/test_slideshow.py`:

```python
from main import validate_timer_seconds, filter_image_files


def test_validate_timer_valid():
    assert validate_timer_seconds(1) == 1
    assert validate_timer_seconds(60) == 60
    assert validate_timer_seconds(10800) == 10800


def test_validate_timer_clamps():
    assert validate_timer_seconds(0) == 1
    assert validate_timer_seconds(-5) == 1
    assert validate_timer_seconds(99999) == 10800


def test_filter_image_files():
    files = [
        "photo.jpg",
        "image.PNG",
        "doc.txt",
        "art.webp",
        "data.csv",
        "pic.gif",
        "shot.bmp",
        "render.jpeg",
    ]
    result = filter_image_files(files)
    assert result == ["photo.jpg", "image.PNG", "art.webp", "pic.gif", "shot.bmp", "render.jpeg"]


def test_filter_image_files_empty():
    assert filter_image_files([]) == []
    assert filter_image_files(["readme.txt", "data.csv"]) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_slideshow.py -v`
Expected: FAIL — ImportError for validate_timer_seconds, filter_image_files

- [ ] **Step 3: Implement validation functions in main.py**

Add to `main.py` after the constants:

```python
import os


def validate_timer_seconds(seconds):
    """Clamp timer value to valid range."""
    return max(TIMER_MIN, min(TIMER_MAX, int(seconds)))


def filter_image_files(file_paths):
    """Return only files with supported image extensions."""
    return [f for f in file_paths if os.path.splitext(f)[1].lower() in SUPPORTED_FORMATS]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_slideshow.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add main.py tests/test_slideshow.py
git commit -m "feat: add timer validation and image file filtering"
```

---

### Task 3: Session save/load logic

**Files:**
- Modify: `main.py`
- Modify: `tests/test_slideshow.py`

- [ ] **Step 1: Write failing tests for session functions**

Add to `tests/test_slideshow.py`:

```python
import json
import tempfile
from main import save_session, load_session


def test_save_and_load_session():
    data = {
        "images": [{"path": "C:/photos/a.jpg", "timer": 60}],
        "timer_mode": "uniform",
        "uniform_timer": 300,
        "order": "sequential",
        "always_on_top": True,
        "loop": True,
        "fit_window": True,
        "lock_aspect": False,
        "window_x": 100,
        "window_y": 200,
        "window_w": 800,
        "window_h": 600,
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        path = f.name

    save_session(data, path)
    loaded = load_session(path)
    assert loaded == data
    os.unlink(path)


def test_load_session_missing_file():
    result = load_session("nonexistent_file_12345.json")
    assert result is None


def test_load_session_corrupted():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("not valid json{{{")
        path = f.name
    result = load_session(path)
    assert result is None
    os.unlink(path)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_slideshow.py -v`
Expected: FAIL — ImportError for save_session, load_session

- [ ] **Step 3: Implement session functions in main.py**

Add to `main.py`:

```python
import json

SESSION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "session.json")


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

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_slideshow.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add main.py tests/test_slideshow.py
git commit -m "feat: add session save/load with JSON persistence"
```

---

### Task 4: Settings window — basic layout with image list

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Create the SettingsWindow class with image list**

Replace the `if __name__` block in `main.py` and add the SettingsWindow class:

```python
from tkinter import filedialog
from PIL import Image, ImageTk


class SettingsWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Slideshow — Настройки")
        self.geometry("500x700")
        ctk.set_appearance_mode("dark")

        self.images = []  # list of {"path": str, "timer": int}
        self.thumbnails = {}  # path -> CTkImage
        self.selected_index = None
        self.drag_start_index = None

        self._build_ui()

    def _build_ui(self):
        # Header with buttons
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(header, text="Картинки", font=("", 16, "bold")).pack(side="left")

        ctk.CTkButton(header, text="+ Папка", width=80, command=self._add_folder).pack(side="right", padx=(5, 0))
        ctk.CTkButton(header, text="+ Файлы", width=80, command=self._add_files).pack(side="right")

        # Scrollable image list
        self.image_list_frame = ctk.CTkScrollableFrame(self, height=250)
        self.image_list_frame.pack(fill="both", expand=True, padx=10, pady=5)

    def _make_thumbnail(self, path):
        """Generate a 48x48 thumbnail for an image file."""
        if path in self.thumbnails:
            return self.thumbnails[path]
        try:
            img = Image.open(path)
            img.thumbnail((48, 48))
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(48, 48))
            self.thumbnails[path] = ctk_img
            return ctk_img
        except Exception:
            return None

    def _add_files(self):
        """Open file dialog to select image files."""
        filetypes = [("Images", " ".join(f"*{ext}" for ext in SUPPORTED_FORMATS))]
        paths = filedialog.askopenfilenames(title="Выбери картинки", filetypes=filetypes)
        for p in paths:
            if p not in [img["path"] for img in self.images]:
                self.images.append({"path": p, "timer": 300})
        self._refresh_image_list()

    def _add_folder(self):
        """Open folder dialog and add all images from it."""
        folder = filedialog.askdirectory(title="Выбери папку с картинками")
        if folder:
            all_files = [os.path.join(folder, f) for f in os.listdir(folder)]
            image_files = filter_image_files(all_files)
            existing = {img["path"] for img in self.images}
            for p in image_files:
                if p not in existing:
                    self.images.append({"path": p, "timer": 300})
            self._refresh_image_list()

    def _refresh_image_list(self):
        """Rebuild the image list UI from self.images."""
        for widget in self.image_list_frame.winfo_children():
            widget.destroy()

        for i, img_data in enumerate(self.images):
            row = ctk.CTkFrame(self.image_list_frame, fg_color="#2a2a44", corner_radius=6)
            row.pack(fill="x", pady=2)
            row.img_index = i

            # Drag-and-drop bindings
            row.bind("<ButtonPress-1>", lambda e, idx=i: self._drag_start(idx))
            row.bind("<B1-Motion>", self._drag_motion)
            row.bind("<ButtonRelease-1>", self._drag_end)

            # Thumbnail
            thumb = self._make_thumbnail(img_data["path"])
            if thumb:
                thumb_label = ctk.CTkLabel(row, image=thumb, text="")
                thumb_label.pack(side="left", padx=(8, 4), pady=4)
                thumb_label.bind("<ButtonPress-1>", lambda e, idx=i: self._drag_start(idx))
                thumb_label.bind("<B1-Motion>", self._drag_motion)
                thumb_label.bind("<ButtonRelease-1>", self._drag_end)

            # Filename
            name = os.path.basename(img_data["path"])
            name_label = ctk.CTkLabel(row, text=name, anchor="w")
            name_label.pack(side="left", fill="x", expand=True, padx=4)
            name_label.bind("<ButtonPress-1>", lambda e, idx=i: self._drag_start(idx))
            name_label.bind("<B1-Motion>", self._drag_motion)
            name_label.bind("<ButtonRelease-1>", self._drag_end)

            # Move up
            ctk.CTkButton(row, text="▲", width=30, command=lambda idx=i: self._move_image(idx, -1)).pack(side="left", padx=2)
            # Move down
            ctk.CTkButton(row, text="▼", width=30, command=lambda idx=i: self._move_image(idx, 1)).pack(side="left", padx=2)
            # Delete
            ctk.CTkButton(row, text="✕", width=30, fg_color="#cc3333", hover_color="#aa2222",
                          command=lambda idx=i: self._delete_image(idx)).pack(side="left", padx=(2, 8))

    def _move_image(self, index, direction):
        """Move image up (-1) or down (+1) in the list."""
        new_index = index + direction
        if 0 <= new_index < len(self.images):
            self.images[index], self.images[new_index] = self.images[new_index], self.images[index]
            self._refresh_image_list()

    def _delete_image(self, index):
        """Remove image from the list."""
        path = self.images[index]["path"]
        self.thumbnails.pop(path, None)
        self.images.pop(index)
        self._refresh_image_list()

    def _drag_start(self, index):
        """Remember which item we started dragging."""
        self.drag_start_index = index

    def _drag_motion(self, event):
        """Track drag position — visual feedback handled by cursor."""
        pass

    def _drag_end(self, event):
        """Drop the item at the current mouse position."""
        if self.drag_start_index is None:
            return
        # Find which row the mouse is over
        widget = self.image_list_frame.winfo_containing(event.x_root, event.y_root)
        target_index = None
        while widget is not None:
            if hasattr(widget, "img_index"):
                target_index = widget.img_index
                break
            widget = widget.master
        if target_index is not None and target_index != self.drag_start_index:
            item = self.images.pop(self.drag_start_index)
            self.images.insert(target_index, item)
            self._refresh_image_list()
        self.drag_start_index = None


if __name__ == "__main__":
    app = SettingsWindow()
    app.mainloop()
```

- [ ] **Step 2: Run the app to verify it opens**

Run: `python main.py`
Expected: Settings window opens with "Картинки" header, "Add Files" and "Add Folder" buttons. Closing the window exits the app.

- [ ] **Step 3: Test adding files and drag/drop manually**

Click "+ Файлы", select some images. Verify thumbnails appear. Try dragging items, clicking ▲/▼, and ✕.

- [ ] **Step 4: Run existing tests to make sure nothing broke**

Run: `python -m pytest tests/test_slideshow.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add main.py
git commit -m "feat: add settings window with image list and drag-drop"
```

---

### Task 5: Settings window — timer controls

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Add timer mode toggle and timer selection to _build_ui**

Add at the end of `_build_ui` method, after the image list:

```python
        # --- Timer Mode ---
        timer_mode_frame = ctk.CTkFrame(self, fg_color="transparent")
        timer_mode_frame.pack(fill="x", padx=10, pady=(10, 5))
        ctk.CTkLabel(timer_mode_frame, text="Режим таймера", font=("", 14, "bold")).pack(anchor="w")

        self.timer_mode_var = ctk.StringVar(value="uniform")
        mode_btn_frame = ctk.CTkFrame(timer_mode_frame, fg_color="transparent")
        mode_btn_frame.pack(fill="x", pady=5)
        ctk.CTkRadioButton(mode_btn_frame, text="Одинаковый для всех", variable=self.timer_mode_var,
                           value="uniform").pack(side="left", padx=(0, 10))
        ctk.CTkRadioButton(mode_btn_frame, text="Индивидуальный", variable=self.timer_mode_var,
                           value="individual").pack(side="left")

        # --- Timer Selection ---
        timer_frame = ctk.CTkFrame(self, fg_color="transparent")
        timer_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(timer_frame, text="Таймер", font=("", 14, "bold")).pack(anchor="w")

        # Quick preset buttons
        presets_frame = ctk.CTkFrame(timer_frame, fg_color="transparent")
        presets_frame.pack(fill="x", pady=5)
        self.preset_buttons = []
        for seconds, label in TIMER_PRESETS:
            btn = ctk.CTkButton(presets_frame, text=label, width=65,
                                command=lambda s=seconds: self._set_timer(s))
            btn.pack(side="left", padx=3)
            self.preset_buttons.append((seconds, btn))

        # Custom time input
        custom_frame = ctk.CTkFrame(timer_frame, fg_color="transparent")
        custom_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(custom_frame, text="Своё время:").pack(side="left", padx=(0, 8))

        self.hours_var = ctk.StringVar(value="0")
        self.mins_var = ctk.StringVar(value="5")
        self.secs_var = ctk.StringVar(value="0")

        ctk.CTkEntry(custom_frame, textvariable=self.hours_var, width=45, justify="center").pack(side="left")
        ctk.CTkLabel(custom_frame, text="ч").pack(side="left", padx=(2, 6))
        ctk.CTkEntry(custom_frame, textvariable=self.mins_var, width=45, justify="center").pack(side="left")
        ctk.CTkLabel(custom_frame, text="мин").pack(side="left", padx=(2, 6))
        ctk.CTkEntry(custom_frame, textvariable=self.secs_var, width=45, justify="center").pack(side="left")
        ctk.CTkLabel(custom_frame, text="сек").pack(side="left", padx=(2, 6))
        ctk.CTkButton(custom_frame, text="OK", width=40, command=self._apply_custom_timer).pack(side="left", padx=5)

        ctk.CTkLabel(timer_frame, text="от 1 секунды до 3 часов", text_color="gray").pack(anchor="w")
```

- [ ] **Step 2: Add timer helper methods**

Add to the SettingsWindow class:

```python
    def _set_timer(self, seconds):
        """Set timer from a preset button."""
        seconds = validate_timer_seconds(seconds)
        if self.timer_mode_var.get() == "uniform":
            for img in self.images:
                img["timer"] = seconds
        else:
            if self.selected_index is not None and self.selected_index < len(self.images):
                self.images[self.selected_index]["timer"] = seconds
        self._refresh_image_list()

    def _apply_custom_timer(self):
        """Read hours/mins/secs fields and apply as timer."""
        try:
            h = int(self.hours_var.get() or 0)
            m = int(self.mins_var.get() or 0)
            s = int(self.secs_var.get() or 0)
        except ValueError:
            return
        total = h * 3600 + m * 60 + s
        self._set_timer(total)
```

- [ ] **Step 3: Run the app and test timer controls**

Run: `python main.py`
Expected: Timer mode toggle, preset buttons, and custom input all visible. Add some images, click preset buttons — timer values update in the image list.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_slideshow.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add main.py
git commit -m "feat: add timer mode toggle and timer selection controls"
```

---

### Task 6: Settings window — order, checkboxes, start button

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Add order toggle, checkboxes, and start button to _build_ui**

Add at the end of `_build_ui`:

```python
        # --- Display Order ---
        order_frame = ctk.CTkFrame(self, fg_color="transparent")
        order_frame.pack(fill="x", padx=10, pady=(10, 5))
        ctk.CTkLabel(order_frame, text="Порядок показа", font=("", 14, "bold")).pack(anchor="w")

        self.order_var = ctk.StringVar(value="sequential")
        order_btn_frame = ctk.CTkFrame(order_frame, fg_color="transparent")
        order_btn_frame.pack(fill="x", pady=5)
        ctk.CTkRadioButton(order_btn_frame, text="По списку", variable=self.order_var,
                           value="sequential").pack(side="left", padx=(0, 10))
        ctk.CTkRadioButton(order_btn_frame, text="Случайный", variable=self.order_var,
                           value="random").pack(side="left")

        # --- Options ---
        options_frame = ctk.CTkFrame(self, fg_color="transparent")
        options_frame.pack(fill="x", padx=10, pady=5)

        self.topmost_var = ctk.BooleanVar(value=False)
        self.loop_var = ctk.BooleanVar(value=True)
        self.fit_window_var = ctk.BooleanVar(value=True)
        self.lock_aspect_var = ctk.BooleanVar(value=False)

        ctk.CTkCheckBox(options_frame, text="Поверх всех окон", variable=self.topmost_var).pack(anchor="w", pady=2)
        ctk.CTkCheckBox(options_frame, text="Зациклить показ", variable=self.loop_var).pack(anchor="w", pady=2)
        ctk.CTkCheckBox(options_frame, text="Подстраивать окно под картинку", variable=self.fit_window_var).pack(anchor="w", pady=2)
        ctk.CTkCheckBox(options_frame, text="Сохранять пропорции окна", variable=self.lock_aspect_var).pack(anchor="w", pady=2)

        # --- Start Button ---
        ctk.CTkButton(self, text="▶  Старт", height=40, font=("", 16, "bold"),
                      command=self._start_slideshow).pack(fill="x", padx=10, pady=15)
```

- [ ] **Step 2: Add placeholder for _start_slideshow**

```python
    def _start_slideshow(self):
        """Launch the viewer window with current settings."""
        if not self.images:
            return
        # Will be implemented in Task 7
        pass
```

- [ ] **Step 3: Run and verify the full settings window**

Run: `python main.py`
Expected: Full settings window with all controls visible — image list, timer, order, checkboxes, start button.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_slideshow.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add main.py
git commit -m "feat: add display order, options checkboxes, and start button"
```

---

### Task 7: Viewer window — image display and hover controls

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Create the ViewerWindow class**

Add to `main.py` before the SettingsWindow class:

```python
class ViewerWindow(ctk.CTkToplevel):
    def __init__(self, master, images, settings):
        super().__init__(master)
        self.title("Slideshow")
        self.configure(fg_color="#1a1a2e")
        self.geometry("800x600")

        self.master_app = master
        self.all_images = images  # list of {"path": str, "timer": int}
        self.settings = settings  # dict with order, loop, fit_window, lock_aspect, topmost
        self.current_index = 0
        self.is_playing = True
        self.timer_id = None
        self.current_aspect = None

        # Apply always-on-top
        self.wm_attributes("-topmost", self.settings["topmost"])

        # Build display order
        self.play_order = list(range(len(self.all_images)))
        if self.settings["order"] == "random":
            import random
            random.shuffle(self.play_order)
        self.order_position = 0

        # Image label (fills entire window)
        self.image_label = ctk.CTkLabel(self, text="", fg_color="#1a1a2e")
        self.image_label.pack(fill="both", expand=True)

        # Hover controls frame (hidden by default)
        self.controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.controls_visible = False

        # Navigation bar
        self.nav_bar = ctk.CTkFrame(self.controls_frame, fg_color="#000000", corner_radius=20)
        self.nav_bar.configure(bg_color="transparent")

        ctk.CTkButton(self.nav_bar, text="⏮", width=40, fg_color="transparent",
                      hover_color="#444", command=self._prev).pack(side="left", padx=5)
        self.play_btn = ctk.CTkButton(self.nav_bar, text="⏸", width=40, fg_color="transparent",
                                       hover_color="#444", command=self._toggle_pause)
        self.play_btn.pack(side="left", padx=5)
        ctk.CTkButton(self.nav_bar, text="⏭", width=40, fg_color="transparent",
                      hover_color="#444", command=self._next).pack(side="left", padx=5)
        self.nav_bar.pack(pady=10)

        # Counter label
        self.counter_label = ctk.CTkLabel(self, text="", font=("", 12),
                                           text_color="rgba(255,255,255,0.7)")
        self.counter_visible = False

        # Bind hover events
        self.bind("<Enter>", self._show_controls)
        self.bind("<Leave>", self._hide_controls)
        self.image_label.bind("<Enter>", self._show_controls)
        self.image_label.bind("<Leave>", self._hide_controls)

        # Bind resize for aspect ratio lock
        self.bind("<Configure>", self._on_resize)
        self._resizing = False

        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Show first image and start timer
        self._show_current_image()
        self._schedule_next()

    def _show_controls(self, event=None):
        if not self.controls_visible:
            self.controls_frame.place(relx=0.5, rely=1.0, anchor="s", y=-10)
            self.controls_visible = True
        if not self.counter_visible:
            self.counter_label.place(relx=1.0, rely=0.0, anchor="ne", x=-10, y=10)
            self.counter_visible = True

    def _hide_controls(self, event=None):
        # Only hide if mouse actually left the window
        x, y = self.winfo_pointerxy()
        wx = self.winfo_rootx()
        wy = self.winfo_rooty()
        ww = self.winfo_width()
        wh = self.winfo_height()
        if not (wx <= x <= wx + ww and wy <= y <= wy + wh):
            self.controls_frame.place_forget()
            self.controls_visible = False
            self.counter_label.place_forget()
            self.counter_visible = False

    def _show_current_image(self):
        """Load and display the current image."""
        if not self.all_images:
            return
        idx = self.play_order[self.order_position]
        path = self.all_images[idx]["path"]
        try:
            pil_img = Image.open(path)
        except Exception:
            self._next()
            return

        self.current_aspect = pil_img.width / pil_img.height

        if self.settings["fit_window"]:
            # Resize window to match image aspect ratio
            win_h = self.winfo_height() or 600
            new_w = int(win_h * self.current_aspect)
            self.geometry(f"{new_w}x{win_h}")

        # Scale image to fit window
        win_w = self.winfo_width() or 800
        win_h = self.winfo_height() or 600
        pil_img.thumbnail((win_w, win_h), Image.LANCZOS)

        ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img,
                                size=(pil_img.width, pil_img.height))
        self.image_label.configure(image=ctk_img)
        self.image_label._current_image = ctk_img  # keep reference

        # Update counter
        total = len(self.all_images)
        display_num = self.order_position + 1
        self.counter_label.configure(text=f"{display_num} / {total}")

    def _schedule_next(self):
        """Schedule the next image transition."""
        if self.timer_id:
            self.after_cancel(self.timer_id)
            self.timer_id = None
        if not self.is_playing:
            return
        idx = self.play_order[self.order_position]
        delay_ms = self.all_images[idx]["timer"] * 1000
        self.timer_id = self.after(delay_ms, self._advance)

    def _advance(self):
        """Move to the next image automatically."""
        self.order_position += 1
        if self.order_position >= len(self.play_order):
            if self.settings["loop"]:
                self.order_position = 0
                if self.settings["order"] == "random":
                    import random
                    random.shuffle(self.play_order)
            else:
                self.order_position = len(self.play_order) - 1
                self.is_playing = False
                self.play_btn.configure(text="▶")
                return
        self._show_current_image()
        self._schedule_next()

    def _next(self):
        """Skip to next image."""
        self.order_position = (self.order_position + 1) % len(self.play_order)
        self._show_current_image()
        if self.is_playing:
            self._schedule_next()

    def _prev(self):
        """Go to previous image."""
        self.order_position = (self.order_position - 1) % len(self.play_order)
        self._show_current_image()
        if self.is_playing:
            self._schedule_next()

    def _toggle_pause(self):
        """Pause or resume the slideshow."""
        self.is_playing = not self.is_playing
        if self.is_playing:
            self.play_btn.configure(text="⏸")
            self._schedule_next()
        else:
            self.play_btn.configure(text="▶")
            if self.timer_id:
                self.after_cancel(self.timer_id)
                self.timer_id = None

    def _on_resize(self, event):
        """Handle window resize — lock aspect ratio if enabled."""
        if self._resizing or not self.current_aspect:
            return
        if self.settings["lock_aspect"] and event.widget == self:
            self._resizing = True
            new_w = event.width
            new_h = int(new_w / self.current_aspect)
            self.geometry(f"{new_w}x{new_h}")
            self._resizing = False
            self._show_current_image()

    def _on_close(self):
        """Stop timer and close viewer."""
        if self.timer_id:
            self.after_cancel(self.timer_id)
        self.destroy()
```

- [ ] **Step 2: Implement _start_slideshow in SettingsWindow**

Replace the placeholder `_start_slideshow`:

```python
    def _start_slideshow(self):
        """Launch the viewer window with current settings."""
        if not self.images:
            return
        settings = {
            "order": self.order_var.get(),
            "loop": self.loop_var.get(),
            "fit_window": self.fit_window_var.get(),
            "lock_aspect": self.lock_aspect_var.get(),
            "topmost": self.topmost_var.get(),
        }
        ViewerWindow(self, self.images, settings)
```

- [ ] **Step 3: Run the app and test the slideshow**

Run: `python main.py`
Expected: Add images, click Start. Viewer opens showing first image. Hover shows controls. ⏮⏸⏭ work. Timer auto-advances. Counter shows "1 / N".

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_slideshow.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add main.py
git commit -m "feat: add viewer window with image display, hover controls, and timer"
```

---

### Task 8: Session persistence — save on close, restore on start

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Add session save to SettingsWindow close**

Add to the SettingsWindow class:

```python
    def _get_session_data(self):
        """Collect all settings into a dict for saving."""
        return {
            "images": self.images,
            "timer_mode": self.timer_mode_var.get(),
            "uniform_timer": 300,
            "order": self.order_var.get(),
            "always_on_top": self.topmost_var.get(),
            "loop": self.loop_var.get(),
            "fit_window": self.fit_window_var.get(),
            "lock_aspect": self.lock_aspect_var.get(),
            "window_x": self.winfo_x(),
            "window_y": self.winfo_y(),
            "window_w": self.winfo_width(),
            "window_h": self.winfo_height(),
        }

    def _on_close(self):
        """Save session and exit."""
        save_session(self._get_session_data())
        self.destroy()
```

- [ ] **Step 2: Add restore dialog and bind close event in __init__**

Add at the end of `__init__`, before `self._build_ui()`:

```python
        self.protocol("WM_DELETE_WINDOW", self._on_close)
```

Add a new method and modify the end of `__init__` (after `self._build_ui()`):

```python
        # Try to restore previous session
        self.after(100, self._check_restore_session)

    def _check_restore_session(self):
        """If session file exists, ask user to restore."""
        data = load_session()
        if data is None:
            return
        dialog = ctk.CTkToplevel(self)
        dialog.title("Восстановить сессию?")
        dialog.geometry("350x150")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="Восстановить прошлую сессию?",
                     font=("", 15, "bold")).pack(pady=(20, 10))

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=10)

        def restore():
            self._apply_session(data)
            dialog.destroy()

        def skip():
            dialog.destroy()

        ctk.CTkButton(btn_frame, text="Да", width=100, command=restore).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Нет", width=100, fg_color="#555", command=skip).pack(side="left", padx=10)

    def _apply_session(self, data):
        """Restore all settings from saved session data."""
        # Restore images (only those that still exist on disk)
        self.images = [img for img in data.get("images", []) if os.path.exists(img["path"])]
        self._refresh_image_list()

        # Restore settings
        self.timer_mode_var.set(data.get("timer_mode", "uniform"))
        self.order_var.set(data.get("order", "sequential"))
        self.topmost_var.set(data.get("always_on_top", False))
        self.loop_var.set(data.get("loop", True))
        self.fit_window_var.set(data.get("fit_window", True))
        self.lock_aspect_var.set(data.get("lock_aspect", False))

        # Restore window position/size
        x = data.get("window_x", 100)
        y = data.get("window_y", 100)
        w = data.get("window_w", 500)
        h = data.get("window_h", 700)
        self.geometry(f"{w}x{h}+{x}+{y}")
```

- [ ] **Step 3: Run the app, add images, close, reopen**

Run: `python main.py`
1. Add a few images, change some settings
2. Close the app
3. Run `python main.py` again
Expected: Dialog "Восстановить прошлую сессию?" appears. Click "Да" — images and settings restored.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_slideshow.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add main.py
git commit -m "feat: add session save on close and restore dialog on start"
```

---

### Task 9: Individual timer display in image list

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Show timer value per image in the list**

Modify `_refresh_image_list` — add timer display after the filename label, inside each row. Find the line with `# Move up` and add before it:

```python
            # Timer display (visible in individual mode or always for info)
            timer_secs = img_data["timer"]
            if timer_secs >= 3600:
                timer_text = f"{timer_secs // 3600}ч {(timer_secs % 3600) // 60}мин"
            elif timer_secs >= 60:
                timer_text = f"{timer_secs // 60} мин"
            else:
                timer_text = f"{timer_secs} сек"
            ctk.CTkLabel(row, text=timer_text, text_color="gray", width=60).pack(side="left", padx=4)
```

- [ ] **Step 2: Add click-to-select for individual timer mode**

Add a click binding in `_refresh_image_list` for each row to set `self.selected_index`:

```python
            # Select on click (for individual timer mode)
            row.bind("<ButtonPress-3>", lambda e, idx=i: self._select_image(idx))
```

Add the method:

```python
    def _select_image(self, index):
        """Select an image for individual timer editing."""
        self.selected_index = index
        self._refresh_image_list()
```

Add visual highlight in `_refresh_image_list` — change the row color if selected:

```python
            bg_color = "#3a3a6a" if i == self.selected_index else "#2a2a44"
            row = ctk.CTkFrame(self.image_list_frame, fg_color=bg_color, corner_radius=6)
```

- [ ] **Step 3: Test individual timer mode**

Run: `python main.py`
1. Add images
2. Switch to "Индивидуальный" timer mode
3. Right-click an image to select it (highlighted)
4. Click a preset button — only that image's timer changes
Expected: Selected image highlighted, timer updated individually.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_slideshow.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add main.py
git commit -m "feat: add individual timer display and selection in image list"
```

---

### Task 10: Final integration and manual testing

**Files:**
- Modify: `main.py` (minor fixes if needed)

- [ ] **Step 1: Add .gitignore for session file**

Create `.gitignore`:

```
session.json
__pycache__/
.superpowers/
```

- [ ] **Step 2: Run full test suite**

Run: `python -m pytest tests/test_slideshow.py -v`
Expected: All PASS

- [ ] **Step 3: Full manual test**

Run: `python main.py`

Test checklist:
1. Add files via "+ Файлы" button — images appear with thumbnails
2. Add folder via "+ Папка" button — all images from folder added
3. Drag-and-drop to reorder — items swap positions
4. ▲/▼ buttons — move items up/down
5. ✕ button — removes image
6. Timer presets — click "5 мин", value updates
7. Custom timer — enter 0h 0min 30sec, click OK
8. Individual mode — right-click to select, set different timers
9. Click "Старт" — viewer opens, shows first image
10. Hover over viewer — controls appear (⏮ ⏸ ⏭) and counter
11. ⏸ pauses, ▶ resumes
12. ⏮ ⏭ navigate manually
13. "Поверх всех окон" — viewer stays on top
14. "Зациклить" off — stops at last image
15. "Подстраивать окно" — window resizes per image
16. "Сохранять пропорции" — locked aspect on manual resize
17. Close app, reopen — restore dialog appears
18. Click "Да" — all settings restored
19. Click "Нет" — fresh start

- [ ] **Step 4: Commit everything**

```bash
git add .gitignore main.py tests/test_slideshow.py
git commit -m "feat: complete image slideshow app with all features"
```
