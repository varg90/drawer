import customtkinter as ctk
import os
import json
from tkinter import filedialog
from PIL import Image, ImageTk

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

SESSION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "session.json")


def validate_timer_seconds(seconds):
    """Clamp timer value to valid range."""
    return max(TIMER_MIN, min(TIMER_MAX, int(seconds)))


def filter_image_files(file_paths):
    """Return only files with supported image extensions."""
    return [f for f in file_paths if os.path.splitext(f)[1].lower() in SUPPORTED_FORMATS]


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


class SettingsWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Slideshow — Настройки")
        self.geometry("500x700")
        ctk.set_appearance_mode("dark")

        self.images = []
        self.thumbnails = {}
        self.selected_index = None
        self.drag_start_index = None

        self._build_ui()

    def _build_ui(self):
        # Header frame with label and add buttons
        header_frame = ctk.CTkFrame(self)
        header_frame.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(header_frame, text="Картинки", font=ctk.CTkFont(size=14, weight="bold")).pack(
            side="left", padx=8, pady=6
        )

        ctk.CTkButton(
            header_frame, text="+ Папка", width=80, command=self._add_folder
        ).pack(side="right", padx=4, pady=6)

        ctk.CTkButton(
            header_frame, text="+ Файлы", width=80, command=self._add_files
        ).pack(side="right", padx=4, pady=6)

        # Scrollable image list frame
        self.image_list_frame = ctk.CTkScrollableFrame(self, height=200)
        self.image_list_frame.pack(fill="both", expand=False, padx=10, pady=(0, 5))

        # --- Timer Mode section ---
        timer_mode_frame = ctk.CTkFrame(self)
        timer_mode_frame.pack(fill="x", padx=10, pady=(5, 2))

        ctk.CTkLabel(
            timer_mode_frame, text="Режим таймера", font=ctk.CTkFont(size=13, weight="bold")
        ).pack(anchor="w", padx=8, pady=(6, 2))

        self.timer_mode_var = ctk.StringVar(value="uniform")

        ctk.CTkRadioButton(
            timer_mode_frame, text="Одинаковый для всех",
            variable=self.timer_mode_var, value="uniform"
        ).pack(anchor="w", padx=20, pady=2)

        ctk.CTkRadioButton(
            timer_mode_frame, text="Индивидуальный",
            variable=self.timer_mode_var, value="individual"
        ).pack(anchor="w", padx=20, pady=(2, 6))

        # --- Timer Selection section ---
        timer_sel_frame = ctk.CTkFrame(self)
        timer_sel_frame.pack(fill="x", padx=10, pady=(2, 5))

        ctk.CTkLabel(
            timer_sel_frame, text="Таймер", font=ctk.CTkFont(size=13, weight="bold")
        ).pack(anchor="w", padx=8, pady=(6, 4))

        # Preset buttons row
        presets_row = ctk.CTkFrame(timer_sel_frame, fg_color="transparent")
        presets_row.pack(fill="x", padx=8, pady=(0, 4))

        for seconds, label in TIMER_PRESETS:
            ctk.CTkButton(
                presets_row, text=label, width=65,
                command=lambda s=seconds: self._set_timer(s)
            ).pack(side="left", padx=2)

        # Custom time input row
        custom_row = ctk.CTkFrame(timer_sel_frame, fg_color="transparent")
        custom_row.pack(fill="x", padx=8, pady=(0, 4))

        ctk.CTkLabel(custom_row, text="Своё время:").pack(side="left", padx=(0, 6))

        self.hours_var = ctk.StringVar(value="0")
        self.mins_var = ctk.StringVar(value="5")
        self.secs_var = ctk.StringVar(value="0")

        ctk.CTkEntry(custom_row, textvariable=self.hours_var, width=45, justify="center").pack(side="left")
        ctk.CTkLabel(custom_row, text="ч").pack(side="left", padx=(2, 6))

        ctk.CTkEntry(custom_row, textvariable=self.mins_var, width=45, justify="center").pack(side="left")
        ctk.CTkLabel(custom_row, text="мин").pack(side="left", padx=(2, 6))

        ctk.CTkEntry(custom_row, textvariable=self.secs_var, width=45, justify="center").pack(side="left")
        ctk.CTkLabel(custom_row, text="сек").pack(side="left", padx=(2, 6))

        ctk.CTkButton(custom_row, text="OK", width=40, command=self._apply_custom_timer).pack(side="left", padx=4)

        # Hint label
        ctk.CTkLabel(
            timer_sel_frame, text="от 1 секунды до 3 часов",
            text_color="gray"
        ).pack(anchor="w", padx=8, pady=(0, 6))

    def _make_thumbnail(self, path):
        """Generate 48x48 CTkImage thumbnail using Pillow, cache in self.thumbnails."""
        if path in self.thumbnails:
            return self.thumbnails[path]
        try:
            img = Image.open(path)
            img.thumbnail((48, 48))
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(48, 48))
            self.thumbnails[path] = ctk_img
            return ctk_img
        except Exception:
            self.thumbnails[path] = None
            return None

    def _add_files(self):
        """Open file dialog, add selected image files to self.images."""
        filetypes = [
            ("Image files", " ".join(f"*{ext}" for ext in SUPPORTED_FORMATS)),
            ("All files", "*.*"),
        ]
        paths = filedialog.askopenfilenames(filetypes=filetypes)
        if not paths:
            return
        existing = {img["path"] for img in self.images}
        for p in filter_image_files(list(paths)):
            if p not in existing:
                self.images.append({"path": p, "timer": 300})
                existing.add(p)
        self._refresh_image_list()

    def _add_folder(self):
        """Open folder dialog, add all image files from the folder."""
        folder = filedialog.askdirectory()
        if not folder:
            return
        all_files = [os.path.join(folder, f) for f in os.listdir(folder)]
        image_files = filter_image_files(all_files)
        existing = {img["path"] for img in self.images}
        for p in image_files:
            if p not in existing:
                self.images.append({"path": p, "timer": 300})
                existing.add(p)
        self._refresh_image_list()

    def _refresh_image_list(self):
        """Destroy all children and rebuild image rows."""
        for widget in self.image_list_frame.winfo_children():
            widget.destroy()

        for i, img_data in enumerate(self.images):
            path = img_data["path"]
            row = ctk.CTkFrame(self.image_list_frame)
            row.pack(fill="x", pady=2, padx=2)
            row.img_index = i

            # Thumbnail
            thumb = self._make_thumbnail(path)
            if thumb is not None:
                thumb_label = ctk.CTkLabel(row, image=thumb, text="")
            else:
                thumb_label = ctk.CTkLabel(row, text="?", width=48, height=48)
            thumb_label.pack(side="left", padx=4, pady=2)
            thumb_label.img_index = i

            # Filename label
            filename = os.path.basename(path)
            name_label = ctk.CTkLabel(row, text=filename, anchor="w")
            name_label.pack(side="left", fill="x", expand=True, padx=4)
            name_label.img_index = i

            # Control buttons
            btn_frame = ctk.CTkFrame(row, fg_color="transparent")
            btn_frame.pack(side="right", padx=4)

            ctk.CTkButton(
                btn_frame, text="▲", width=28, height=28,
                command=lambda idx=i: self._move_image(idx, -1)
            ).pack(side="left", padx=1)

            ctk.CTkButton(
                btn_frame, text="▼", width=28, height=28,
                command=lambda idx=i: self._move_image(idx, 1)
            ).pack(side="left", padx=1)

            ctk.CTkButton(
                btn_frame, text="✕", width=28, height=28,
                command=lambda idx=i: self._delete_image(idx)
            ).pack(side="left", padx=1)

            # Drag-drop bindings
            for widget in (row, thumb_label, name_label):
                widget.bind("<ButtonPress-1>", lambda e, idx=i: self._drag_start(idx))
                widget.bind("<B1-Motion>", self._drag_motion)
                widget.bind("<ButtonRelease-1>", self._drag_end)

    def _move_image(self, index, direction):
        """Swap image at index with the one in the given direction."""
        new_index = index + direction
        if 0 <= new_index < len(self.images):
            self.images[index], self.images[new_index] = self.images[new_index], self.images[index]
            self._refresh_image_list()

    def _delete_image(self, index):
        """Remove image from list and clear its cached thumbnail."""
        path = self.images[index]["path"]
        self.images.pop(index)
        if path in self.thumbnails:
            del self.thumbnails[path]
        if self.selected_index == index:
            self.selected_index = None
        elif self.selected_index is not None and self.selected_index > index:
            self.selected_index -= 1
        self._refresh_image_list()

    def _drag_start(self, index):
        """Record the starting index for a drag operation."""
        self.drag_start_index = index

    def _drag_motion(self, event):
        pass

    def _set_timer(self, seconds):
        """Set timer: all images in uniform mode, or selected image in individual mode."""
        seconds = validate_timer_seconds(seconds)
        if self.timer_mode_var.get() == "uniform":
            for img in self.images:
                img["timer"] = seconds
        else:
            if self.selected_index is not None and 0 <= self.selected_index < len(self.images):
                self.images[self.selected_index]["timer"] = seconds
        self._refresh_image_list()

    def _apply_custom_timer(self):
        """Parse h/m/s entry fields and apply the resulting timer value."""
        try:
            h = int(self.hours_var.get() or 0)
            m = int(self.mins_var.get() or 0)
            s = int(self.secs_var.get() or 0)
            total = h * 3600 + m * 60 + s
            self._set_timer(total)
        except ValueError:
            pass

    def _drag_end(self, event):
        """Complete drag-drop by finding the target row under the cursor."""
        if self.drag_start_index is None:
            return
        widget_under = self.winfo_containing(event.x_root, event.y_root)
        target_index = None
        while widget_under is not None:
            if hasattr(widget_under, "img_index"):
                target_index = widget_under.img_index
                break
            widget_under = widget_under.master if hasattr(widget_under, "master") else None

        if target_index is not None and target_index != self.drag_start_index:
            item = self.images.pop(self.drag_start_index)
            self.images.insert(target_index, item)
            self._refresh_image_list()

        self.drag_start_index = None


if __name__ == "__main__":
    app = SettingsWindow()
    app.mainloop()
