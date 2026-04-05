import customtkinter as ctk
import os
import json
import random
from tkinter import filedialog, BooleanVar
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


class ViewerWindow(ctk.CTkToplevel):
    def __init__(self, master, images, settings):
        super().__init__(master)
        self.title("Slideshow")
        self.configure(fg_color="#1a1a2e")
        self.geometry("800x600")

        self.master_app = master
        self.all_images = images  # list of {"path": str, "timer": int}
        self.settings = settings  # dict with order, loop, fit_window, lock_aspect, topmost
        self.is_playing = True
        self.timer_id = None
        self.current_aspect = None
        self._resizing = False

        # Always-on-top
        self.wm_attributes("-topmost", self.settings["topmost"])

        # Build play order
        self.play_order = list(range(len(self.all_images)))
        if self.settings["order"] == "random":
            random.shuffle(self.play_order)
        self.order_position = 0

        # Image label fills entire window
        self.image_label = ctk.CTkLabel(self, text="", fg_color="#1a1a2e")
        self.image_label.pack(fill="both", expand=True)

        # Hover controls (hidden by default)
        self.controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.controls_visible = False

        # Navigation bar
        self.nav_bar = ctk.CTkFrame(self.controls_frame, fg_color="#000000", corner_radius=20)
        ctk.CTkButton(self.nav_bar, text="⏮", width=40, fg_color="transparent",
                      hover_color="#444", command=self._prev).pack(side="left", padx=5)
        self.play_btn = ctk.CTkButton(self.nav_bar, text="⏸", width=40, fg_color="transparent",
                                       hover_color="#444", command=self._toggle_pause)
        self.play_btn.pack(side="left", padx=5)
        ctk.CTkButton(self.nav_bar, text="⏭", width=40, fg_color="transparent",
                      hover_color="#444", command=self._next).pack(side="left", padx=5)
        self.nav_bar.pack(pady=10)

        # Counter label
        self.counter_label = ctk.CTkLabel(self, text="", font=("", 12), text_color="#aaaaaa")
        self.counter_visible = False

        # Hover bindings
        self.bind("<Enter>", self._show_controls)
        self.bind("<Leave>", self._hide_controls)
        self.image_label.bind("<Enter>", self._show_controls)
        self.image_label.bind("<Leave>", self._hide_controls)

        # Resize binding for aspect lock
        self.bind("<Configure>", self._on_resize)

        # Close handler
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Show first image and start
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
        x, y = self.winfo_pointerxy()
        wx, wy = self.winfo_rootx(), self.winfo_rooty()
        ww, wh = self.winfo_width(), self.winfo_height()
        if not (wx <= x <= wx + ww and wy <= y <= wy + wh):
            self.controls_frame.place_forget()
            self.controls_visible = False
            self.counter_label.place_forget()
            self.counter_visible = False

    def _show_current_image(self):
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
            win_h = self.winfo_height() or 600
            new_w = int(win_h * self.current_aspect)
            self.geometry(f"{new_w}x{win_h}")

        win_w = self.winfo_width() or 800
        win_h = self.winfo_height() or 600
        pil_img.thumbnail((win_w, win_h), Image.LANCZOS)
        ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img,
                                size=(pil_img.width, pil_img.height))
        self.image_label.configure(image=ctk_img)
        self.image_label._current_image = ctk_img

        total = len(self.all_images)
        self.counter_label.configure(text=f"{self.order_position + 1} / {total}")

    def _schedule_next(self):
        if self.timer_id:
            self.after_cancel(self.timer_id)
            self.timer_id = None
        if not self.is_playing:
            return
        idx = self.play_order[self.order_position]
        delay_ms = self.all_images[idx]["timer"] * 1000
        self.timer_id = self.after(delay_ms, self._advance)

    def _advance(self):
        self.order_position += 1
        if self.order_position >= len(self.play_order):
            if self.settings["loop"]:
                self.order_position = 0
                if self.settings["order"] == "random":
                    random.shuffle(self.play_order)
            else:
                self.order_position = len(self.play_order) - 1
                self.is_playing = False
                self.play_btn.configure(text="▶")
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
        if self.is_playing:
            self.play_btn.configure(text="⏸")
            self._schedule_next()
        else:
            self.play_btn.configure(text="▶")
            if self.timer_id:
                self.after_cancel(self.timer_id)
                self.timer_id = None

    def _on_resize(self, event):
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
        if self.timer_id:
            self.after_cancel(self.timer_id)
        self.destroy()


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

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build_ui()
        self.after(100, self._check_restore_session)

    def _get_session_data(self):
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
        save_session(self._get_session_data())
        self.destroy()

    def _check_restore_session(self):
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
        self.images = [img for img in data.get("images", []) if os.path.exists(img["path"])]
        self._refresh_image_list()
        self.timer_mode_var.set(data.get("timer_mode", "uniform"))
        self.order_var.set(data.get("order", "sequential"))
        self.topmost_var.set(data.get("always_on_top", False))
        self.loop_var.set(data.get("loop", True))
        self.fit_window_var.set(data.get("fit_window", True))
        self.lock_aspect_var.set(data.get("lock_aspect", False))
        x = data.get("window_x", 100)
        y = data.get("window_y", 100)
        w = data.get("window_w", 500)
        h = data.get("window_h", 700)
        self.geometry(f"{w}x{h}+{x}+{y}")

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

        # --- Display Order section ---
        order_frame = ctk.CTkFrame(self)
        order_frame.pack(fill="x", padx=10, pady=(2, 5))

        ctk.CTkLabel(
            order_frame, text="Порядок показа", font=ctk.CTkFont(size=13, weight="bold")
        ).pack(anchor="w", padx=8, pady=(6, 2))

        self.order_var = ctk.StringVar(value="sequential")

        ctk.CTkRadioButton(
            order_frame, text="По списку",
            variable=self.order_var, value="sequential"
        ).pack(anchor="w", padx=20, pady=2)

        ctk.CTkRadioButton(
            order_frame, text="Случайный",
            variable=self.order_var, value="random"
        ).pack(anchor="w", padx=20, pady=(2, 6))

        # --- Options section ---
        options_frame = ctk.CTkFrame(self)
        options_frame.pack(fill="x", padx=10, pady=(2, 5))

        self.topmost_var = BooleanVar(value=False)
        self.loop_var = BooleanVar(value=True)
        self.fit_window_var = BooleanVar(value=True)
        self.lock_aspect_var = BooleanVar(value=False)

        ctk.CTkCheckBox(options_frame, text="Поверх всех окон", variable=self.topmost_var).pack(
            anchor="w", padx=20, pady=(6, 2)
        )
        ctk.CTkCheckBox(options_frame, text="Зациклить показ", variable=self.loop_var).pack(
            anchor="w", padx=20, pady=2
        )
        ctk.CTkCheckBox(
            options_frame, text="Подстраивать окно под картинку", variable=self.fit_window_var
        ).pack(anchor="w", padx=20, pady=2)
        ctk.CTkCheckBox(
            options_frame, text="Сохранять пропорции окна", variable=self.lock_aspect_var
        ).pack(anchor="w", padx=20, pady=(2, 6))

        # --- Start button ---
        ctk.CTkButton(
            self, text="▶  Старт", height=40,
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self._start_slideshow
        ).pack(fill="x", padx=10, pady=(5, 10))

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
            bg_color = "#3a3a6a" if i == self.selected_index else None  # None = default
            row = ctk.CTkFrame(self.image_list_frame, fg_color=bg_color)
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

            # Timer display
            timer_secs = img_data["timer"]
            if timer_secs >= 3600:
                timer_text = f"{timer_secs // 3600}ч {(timer_secs % 3600) // 60}мин"
            elif timer_secs >= 60:
                timer_text = f"{timer_secs // 60} мин"
            else:
                timer_text = f"{timer_secs} сек"
            ctk.CTkLabel(row, text=timer_text, text_color="gray", width=60).pack(side="left", padx=4)

            # Right-click to select for individual timer mode
            row.bind("<ButtonPress-3>", lambda e, idx=i: self._select_image(idx))

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

    def _select_image(self, index):
        self.selected_index = index
        self._refresh_image_list()

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

    def _start_slideshow(self):
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
