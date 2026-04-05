import customtkinter as ctk
import os
import sys
import json
import random
import logging
from tkinter import filedialog, BooleanVar
from PIL import Image, ImageTk

# Resolve app directory (works both as .py and as .exe)
if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

# Logging setup
LOG_FILE = os.path.join(APP_DIR, "app.log")
logging.basicConfig(
    filename=LOG_FILE, level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S", encoding="utf-8"
)
log = logging.getLogger("refbot")

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

SESSION_FILE = os.path.join(APP_DIR, "session.json")


def format_time(s):
    """Format seconds into human-readable time string."""
    if s >= 3600:
        return f"{s // 3600}:{(s % 3600) // 60:02d}:{s % 60:02d}"
    elif s >= 60:
        return f"{s // 60}:{s % 60:02d}"
    else:
        return f"0:{s:02d}"


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
        self.title("RefBot")
        self.configure(fg_color="#000000", bg="#000000")
        self.overrideredirect(True)  # Borderless window
        self.geometry("800x600")

        self.master_app = master
        self.all_images = images  # list of {"path": str, "timer": int}
        self.settings = settings  # dict with order, fit_window, lock_aspect, topmost
        self.is_playing = True
        self.timer_id = None
        self.current_aspect = None
        self._resize_timer = None
        self._countdown_remaining = 0
        self._countdown_timer_id = None

        # Always-on-top
        self.wm_attributes("-topmost", self.settings["topmost"])

        # Build play order
        self.play_order = list(range(len(self.all_images)))
        if self.settings["order"] == "random":
            random.shuffle(self.play_order)
        self.order_position = 0

        # Image canvas fills entire window (pure black, no CTk color leaking)
        import tkinter as tk
        self.image_canvas = tk.Canvas(self, bg="#000000", highlightthickness=0)
        self.image_canvas.pack(fill="both", expand=True)
        self._canvas_image_id = None

        # Hover controls (hidden by default)
        self.controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.controls_visible = False

        # Navigation bar
        self.nav_bar = ctk.CTkFrame(self.controls_frame, fg_color="#000000", corner_radius=20)
        self._build_nav_buttons()
        self.nav_bar.pack(pady=10)

        # Counter label
        self.counter_label = ctk.CTkLabel(self, text="", font=("", 12), text_color="#aaaaaa")
        self.counter_visible = False


        # Hover bindings
        self.bind("<Enter>", self._show_controls)
        self.bind("<Leave>", self._hide_controls)
        self.image_canvas.bind("<Enter>", self._show_controls)
        self.image_canvas.bind("<Leave>", self._hide_controls)

        # Right-click drag to move window
        self._drag_x = 0
        self._drag_y = 0
        self.image_canvas.bind("<ButtonPress-3>", self._window_drag_start)
        self.image_canvas.bind("<B3-Motion>", self._window_drag_move)

        # Resize grip area (all corners)
        self._resize_grip_size = 50
        self._resizing_window = False
        self._resize_corner = None  # "tl", "tr", "bl", "br"
        self.image_canvas.bind("<Motion>", self._update_cursor)
        self.image_canvas.bind("<ButtonPress-1>", self._resize_start)
        self.image_canvas.bind("<B1-Motion>", self._resize_drag)
        self.image_canvas.bind("<ButtonRelease-1>", self._resize_end)

        # Resize binding for aspect lock
        self.bind("<Configure>", self._on_resize)

        # Close handler
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Show first image and start
        self._show_current_image()
        self._schedule_next()

    def _build_nav_buttons(self):
        """Create nav buttons with current size."""
        for w in self.nav_bar.winfo_children():
            w.destroy()
        btn_size, font_size, pad = self._calc_nav_size()
        font = ("", font_size)
        ctk.CTkButton(self.nav_bar, text="⏮", width=btn_size, height=btn_size,
                      font=font, fg_color="transparent",
                      hover_color="#444", command=self._prev).pack(side="left", padx=pad)
        self.play_btn = ctk.CTkButton(self.nav_bar, text="⏸" if self.is_playing else "▶",
                                       width=btn_size, height=btn_size,
                                       font=font, fg_color="transparent",
                                       hover_color="#444", command=self._toggle_pause)
        self.play_btn.pack(side="left", padx=pad)
        ctk.CTkButton(self.nav_bar, text="⏭", width=btn_size, height=btn_size,
                      font=font, fg_color="transparent",
                      hover_color="#444", command=self._next).pack(side="left", padx=pad)
        # Timer countdown label
        self.timer_label = ctk.CTkLabel(self.nav_bar, text="", font=font,
                                         text_color="#aaaaaa", width=btn_size)
        self.timer_label.pack(side="left", padx=pad)

        ctk.CTkButton(self.nav_bar, text="⚙", width=btn_size, height=btn_size,
                      font=font, fg_color="transparent",
                      hover_color="#444", command=self._open_settings).pack(side="left", padx=pad)
        ctk.CTkButton(self.nav_bar, text="✕", width=btn_size, height=btn_size,
                      font=font, fg_color="transparent",
                      hover_color="#662222", command=self._on_close).pack(side="left", padx=pad)

    def _calc_nav_size(self):
        """Calculate button size based on window size."""
        win_w = self.winfo_width() or 800
        win_h = self.winfo_height() or 600
        smallest = min(win_w, win_h)
        # Button size: 8% of smallest dimension, clamped 24-60px
        btn_size = max(24, min(60, int(smallest * 0.08)))
        font_size = max(10, min(24, int(btn_size * 0.5)))
        pad = max(2, min(8, int(btn_size * 0.1)))
        return btn_size, font_size, pad

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
            self._current_pil_img = Image.open(path)
        except Exception as e:
            log.error(f"Failed to open image: {path} — {e}")
            self._next()
            return

        img_w, img_h = self._current_pil_img.width, self._current_pil_img.height
        self.current_aspect = img_w / img_h

        # Lock aspect ratio via window manager
        if self.settings["lock_aspect"]:
            self.wm_aspect(img_w, img_h, img_w, img_h)
        else:
            self.wm_aspect()

        # Fit window to image on image change (not on manual resize)
        if self.settings["fit_window"]:
            win_h = self.winfo_height() or 600
            new_w = int(win_h * self.current_aspect)
            self.geometry(f"{new_w}x{win_h}")

        self._update_image_display()

        total = len(self.all_images)
        _, font_size, _ = self._calc_nav_size()
        self.counter_label.configure(text=f"{self.order_position + 1} / {total}",
                                      font=("", font_size))

    def _update_image_display(self):
        """Rescale current image to fit the current window size."""
        if not hasattr(self, "_current_pil_img") or self._current_pil_img is None:
            return
        img_w, img_h = self._current_pil_img.width, self._current_pil_img.height
        canvas_w = self.image_canvas.winfo_width() or 800
        canvas_h = self.image_canvas.winfo_height() or 600

        scale = min(canvas_w / img_w, canvas_h / img_h)
        display_w = max(1, int(img_w * scale))
        display_h = max(1, int(img_h * scale))

        resized = self._current_pil_img.resize((display_w, display_h), Image.LANCZOS)
        self._tk_photo = ImageTk.PhotoImage(resized)

        # Center image on canvas
        cx = canvas_w // 2
        cy = canvas_h // 2
        self.image_canvas.delete("all")
        self._canvas_image_id = self.image_canvas.create_image(cx, cy, image=self._tk_photo)

        # Update nav button sizes
        self._build_nav_buttons()

    def _schedule_next(self):
        if self.timer_id:
            self.after_cancel(self.timer_id)
            self.timer_id = None
        if self._countdown_timer_id:
            self.after_cancel(self._countdown_timer_id)
            self._countdown_timer_id = None
        if not self.is_playing:
            self._update_timer_label()
            return
        idx = self.play_order[self.order_position]
        self._countdown_remaining = self.all_images[idx]["timer"]
        self._update_timer_label()
        self._start_countdown()

    def _start_countdown(self):
        """Tick countdown every second and advance when done."""
        if self._countdown_remaining <= 0:
            self._advance()
            return
        self._countdown_remaining -= 1
        self._update_timer_label()
        self._countdown_timer_id = self.after(1000, self._start_countdown)

    def _format_time(self, s):
        return format_time(s)

    def _update_timer_label(self):
        """Update the timer display in the nav bar and warning overlay."""
        if not hasattr(self, "timer_label"):
            return
        s = self._countdown_remaining
        warn_on = self.settings.get("warn_enabled", False)
        warn_secs = self.settings.get("warn_seconds", 10)
        is_warning = warn_on and self.is_playing and s <= warn_secs

        # Nav bar timer
        if not self.is_playing:
            self.timer_label.configure(text="⏸", text_color="#aaaaaa")
        else:
            color = "#ff3333" if is_warning else "#aaaaaa"
            self.timer_label.configure(text=self._format_time(s), text_color=color)

        # Warning overlay on canvas
        self.image_canvas.delete("warning_timer")
        if is_warning and self.is_playing:
            canvas_w = self.image_canvas.winfo_width()
            canvas_h = self.image_canvas.winfo_height()
            font_size = max(16, min(48, int(min(canvas_w, canvas_h) * 0.08)))
            self.image_canvas.create_text(
                canvas_w // 2, canvas_h - 30,
                text=self._format_time(s),
                fill="#ff3333", font=("", font_size, "bold"),
                tags="warning_timer"
            )

    def _advance(self):
        self.order_position += 1
        if self.order_position >= len(self.play_order):
            # End of list — close viewer and open settings
            self._on_close()
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
            self._start_countdown()  # Resume from remaining time
        else:
            self.play_btn.configure(text="▶")
            if self._countdown_timer_id:
                self.after_cancel(self._countdown_timer_id)
                self._countdown_timer_id = None
            self._update_timer_label()

    def _on_resize(self, event):
        if event.widget != self:
            return
        if self._resizing_window:
            return  # Handled by _resize_drag/_resize_end
        # Debounce: update image after resize stops (150ms)
        if self._resize_timer:
            self.after_cancel(self._resize_timer)
        self._resize_timer = self.after(150, self._update_image_display)

    def _get_corner(self, event):
        """Determine which corner the mouse is in, or None."""
        cw = self.image_canvas.winfo_width()
        ch = self.image_canvas.winfo_height()
        g = self._resize_grip_size
        left = event.x < g
        right = event.x >= cw - g
        top = event.y < g
        bottom = event.y >= ch - g
        if top and left:
            return "tl"
        if top and right:
            return "tr"
        if bottom and left:
            return "bl"
        if bottom and right:
            return "br"
        return None

    def _update_cursor(self, event):
        corner = self._get_corner(event)
        if corner in ("tl", "br"):
            self.image_canvas.configure(cursor="size_nw_se")
        elif corner in ("tr", "bl"):
            self.image_canvas.configure(cursor="size_ne_sw")
        else:
            self.image_canvas.configure(cursor="")

    def _resize_start(self, event):
        corner = self._get_corner(event)
        if corner:
            self._resizing_window = True
            self._resize_corner = corner
            self._resize_start_x = event.x_root
            self._resize_start_y = event.y_root
            self._resize_start_w = self.winfo_width()
            self._resize_start_h = self.winfo_height()
            self._resize_start_win_x = self.winfo_x()
            self._resize_start_win_y = self.winfo_y()

    def _resize_drag(self, event):
        if not self._resizing_window:
            return
        dx = event.x_root - self._resize_start_x
        dy = event.y_root - self._resize_start_y
        c = self._resize_corner
        x = self._resize_start_win_x
        y = self._resize_start_win_y
        w = self._resize_start_w
        h = self._resize_start_h

        if c == "br":
            new_w = max(200, w + dx)
            new_h = max(150, h + dy)
        elif c == "bl":
            new_w = max(200, w - dx)
            new_h = max(150, h + dy)
            x = x + w - new_w
        elif c == "tr":
            new_w = max(200, w + dx)
            new_h = max(150, h - dy)
            y = y + h - new_h
        elif c == "tl":
            new_w = max(200, w - dx)
            new_h = max(150, h - dy)
            x = x + w - new_w
            y = y + h - new_h

        if self.settings["lock_aspect"] and self.current_aspect:
            target_h = int(new_w / self.current_aspect)
            if target_h >= new_h:
                if c in ("tl", "tr"):
                    y = y - (target_h - new_h)
                new_h = target_h
            else:
                target_w = int(new_h * self.current_aspect)
                if c in ("tl", "bl"):
                    x = x - (target_w - new_w)
                new_w = target_w

        self.geometry(f"{new_w}x{new_h}+{x}+{y}")

    def _resize_end(self, event):
        if self._resizing_window:
            self._resizing_window = False
            self._update_image_display()

    def _window_drag_start(self, event):
        self._drag_x = event.x_root - self.winfo_x()
        self._drag_y = event.y_root - self.winfo_y()

    def _window_drag_move(self, event):
        x = event.x_root - self._drag_x
        y = event.y_root - self._drag_y
        self.geometry(f"+{x}+{y}")

    def _open_settings(self):
        """Show the settings window."""
        self.master_app.deiconify()
        self.master_app.lift()

    def _on_close(self):
        if self.timer_id:
            self.after_cancel(self.timer_id)
        if self._countdown_timer_id:
            self.after_cancel(self._countdown_timer_id)
        self.master_app.deiconify()  # Show settings when viewer closes
        self.destroy()


class SettingsWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        # Enable drag-and-drop
        self.title("RefBot — Настройки")
        self.geometry("500x700")
        self.minsize(400, 500)
        ctk.set_appearance_mode("dark")

        self.images = []
        self.thumbnails = {}
        self.selected_index = None
        self.drag_start_index = None
        self._drag_moved = False
        self._drag_start_x = None
        self._drag_start_y = None

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.withdraw()  # Hide window while building UI
        self._build_ui()
        self.after(100, self._show_window)


    def _init_dnd(self):
        """Drag-and-drop not available on Python 3.14/Windows due to GIL restrictions."""
        pass

    def _on_drop(self, file_list):
        """Handle files dropped onto the window."""
        existing = {img["path"] for img in self.images}
        added = False
        for p in file_list:
            if os.path.isdir(p):
                all_files = [os.path.join(p, f) for f in os.listdir(p)]
                for img_path in filter_image_files(all_files):
                    if img_path not in existing:
                        self.images.append({"path": img_path, "timer": 300})
                        existing.add(img_path)
                        added = True
            elif os.path.isfile(p) and os.path.splitext(p)[1].lower() in SUPPORTED_FORMATS:
                if p not in existing:
                    self.images.append({"path": p, "timer": 300})
                    existing.add(p)
                    added = True
        if added:
            self._refresh_image_list()
            if self._images_collapsed:
                self._toggle_image_list()

    def _show_window(self):
        self.deiconify()  # Show window after layout is ready
        self._init_dnd()
        self._check_restore_session()

    def _get_session_data(self):
        return {
            "images": self.images,
            "timer_mode": self.timer_mode_var.get(),
            "uniform_timer": 300,
            "order": self.order_var.get(),
            "always_on_top": self.topmost_var.get(),
            "fit_window": self.fit_window_var.get(),
            "lock_aspect": self.lock_aspect_var.get(),
            "show_filename": self.show_filename_var.get(),
            "warn_enabled": self.warn_enabled_var.get(),
            "warn_mins": self.warn_mins_var.get(),
            "warn_secs": self.warn_secs_var.get(),
            "window_x": self.winfo_x(),
            "window_y": self.winfo_y(),
            "window_w": self.winfo_width(),
            "window_h": self.winfo_height(),
        }

    def _on_close(self):
        save_session(self._get_session_data())
        # If viewer is active, just hide settings instead of quitting
        if hasattr(self, "viewer") and self.viewer and self.viewer.winfo_exists():
            self.withdraw()
        else:
            self.destroy()

    def _check_restore_session(self):
        data = load_session()
        if data is None:
            return
        dialog = ctk.CTkToplevel(self)
        dialog.title("Восстановить сессию?")
        dialog.resizable(False, False)
        dialog.transient(self)

        # Center dialog on settings window
        dw, dh = 350, 150
        self.update_idletasks()
        wx = self.winfo_x()
        wy = self.winfo_y()
        ww = self.winfo_width()
        wh = self.winfo_height()
        x = wx + (ww - dw) // 2
        y = wy + (wh - dh) // 2
        dialog.geometry(f"{dw}x{dh}+{x}+{y}")
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
        # Collapse image list on restore
        if not self._images_collapsed:
            self._toggle_image_list()
        self.timer_mode_var.set(data.get("timer_mode", "uniform"))
        self.order_var.set(data.get("order", "sequential"))
        self.random_order_var.set(self.order_var.get() == "random")
        self.topmost_var.set(data.get("always_on_top", False))
        # fit_window and lock_aspect are always True now
        self.show_filename_var.set(data.get("show_filename", False))
        self.warn_enabled_var.set(data.get("warn_enabled", False))
        self.warn_mins_var.set(data.get("warn_mins", "0"))
        self.warn_secs_var.set(data.get("warn_secs", "10"))
        x = data.get("window_x", 100)
        y = data.get("window_y", 100)
        w = data.get("window_w", 500)
        h = data.get("window_h", 700)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self):
        # Start button fixed at bottom (pack first with side="bottom")
        ctk.CTkButton(
            self, text="▶  Старт", height=40,
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self._start_slideshow
        ).pack(fill="x", padx=10, pady=(5, 10), side="bottom")

        # Scrollable content area
        self._content = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._content.pack(fill="both", expand=True, padx=0, pady=0)

        # Header frame with label, collapse toggle, and add buttons
        header_frame = ctk.CTkFrame(self._content)
        header_frame.pack(fill="x", padx=10, pady=(10, 5))

        self._images_collapsed = False
        self._collapse_btn = ctk.CTkButton(
            header_frame, text="▼", width=30, fg_color="transparent",
            hover_color="#444", command=self._toggle_image_list
        )
        self._collapse_btn.pack(side="left", padx=(4, 0), pady=6)

        ctk.CTkLabel(header_frame, text="Картинки", font=ctk.CTkFont(size=14, weight="bold")).pack(
            side="left", padx=4, pady=6
        )

        ctk.CTkButton(
            header_frame, text="Очистить", width=70, fg_color="#555",
            hover_color="#773333", command=self._clear_images
        ).pack(side="right", padx=4, pady=6)

        ctk.CTkOptionMenu(
            header_frame, values=["Файлы", "Папка"],
            command=self._on_add_selected, width=80
        ).pack(side="right", padx=4, pady=6)

        self.show_filename_var = BooleanVar(value=False)

        # Image list frame (collapsible)
        self.image_list_frame = ctk.CTkFrame(self._content)
        self.image_list_frame.pack(fill="x", padx=10, pady=(0, 5))

        # --- Timer Selection section ---
        timer_sel_frame = ctk.CTkFrame(self._content)
        timer_sel_frame.pack(fill="x", padx=10, pady=(2, 5))

        ctk.CTkLabel(
            timer_sel_frame, text="Таймер", font=ctk.CTkFont(size=13, weight="bold")
        ).pack(anchor="w", padx=8, pady=(6, 2))

        # Timer mode
        self.timer_mode_var = ctk.StringVar(value="uniform")
        mode_row = ctk.CTkFrame(timer_sel_frame, fg_color="transparent")
        mode_row.pack(fill="x", padx=8, pady=(0, 4))
        ctk.CTkRadioButton(
            mode_row, text="Стандартный",
            variable=self.timer_mode_var, value="uniform"
        ).pack(side="left", padx=(0, 10))
        ctk.CTkRadioButton(
            mode_row, text="Настраиваемый",
            variable=self.timer_mode_var, value="individual"
        ).pack(side="left")

        # Preset dropdown
        self._preset_row = ctk.CTkFrame(timer_sel_frame, fg_color="transparent")
        self._preset_row.pack(fill="x", padx=8, pady=(0, 4))

        preset_labels = [label for _, label in TIMER_PRESETS] + ["Своё время..."]
        self._preset_map = {label: seconds for seconds, label in TIMER_PRESETS}
        self.preset_var = ctk.StringVar(value=preset_labels[1])  # default "5 мин"
        ctk.CTkOptionMenu(
            self._preset_row, variable=self.preset_var, values=preset_labels,
            command=self._on_preset_selected, width=140
        ).pack(side="left")

        # Custom time input row (hidden by default, shown when "Своё время..." selected)
        self.custom_row = ctk.CTkFrame(timer_sel_frame, fg_color="transparent")

        self.hours_var = ctk.StringVar(value="0")
        self.mins_var = ctk.StringVar(value="5")
        self.secs_var = ctk.StringVar(value="0")

        ctk.CTkEntry(self.custom_row, textvariable=self.hours_var, width=45, justify="center").pack(side="left")
        ctk.CTkLabel(self.custom_row, text="ч").pack(side="left", padx=(2, 6))

        ctk.CTkEntry(self.custom_row, textvariable=self.mins_var, width=45, justify="center").pack(side="left")
        ctk.CTkLabel(self.custom_row, text="мин").pack(side="left", padx=(2, 6))

        ctk.CTkEntry(self.custom_row, textvariable=self.secs_var, width=45, justify="center").pack(side="left")
        ctk.CTkLabel(self.custom_row, text="сек").pack(side="left", padx=(2, 6))

        ctk.CTkButton(self.custom_row, text="OK", width=40, command=self._apply_custom_timer).pack(side="left", padx=4)

        ctk.CTkLabel(self.custom_row, text="(1сек — 3ч)", text_color="gray",
                     font=ctk.CTkFont(size=11)).pack(side="left", padx=4)

        # --- Timer Warning section ---
        warn_frame = ctk.CTkFrame(timer_sel_frame, fg_color="transparent")
        warn_frame.pack(fill="x", padx=8, pady=(0, 6))

        self.warn_enabled_var = BooleanVar(value=False)
        ctk.CTkCheckBox(warn_frame, text="Предупреждение за",
                        variable=self.warn_enabled_var).pack(side="left")

        self.warn_mins_var = ctk.StringVar(value="0")
        ctk.CTkEntry(warn_frame, textvariable=self.warn_mins_var,
                     width=45, justify="center").pack(side="left", padx=4)
        ctk.CTkLabel(warn_frame, text="мин").pack(side="left", padx=(0, 4))

        self.warn_secs_var = ctk.StringVar(value="10")
        ctk.CTkEntry(warn_frame, textvariable=self.warn_secs_var,
                     width=45, justify="center").pack(side="left", padx=4)
        ctk.CTkLabel(warn_frame, text="сек до конца").pack(side="left")

        # --- Options section ---
        self.order_var = ctk.StringVar(value="sequential")
        options_frame = ctk.CTkFrame(self._content)
        options_frame.pack(fill="x", padx=10, pady=(2, 5))

        self.topmost_var = BooleanVar(value=False)
        self.random_order_var = BooleanVar(value=False)
        self.fit_window_var = BooleanVar(value=True)  # Always on
        self.lock_aspect_var = BooleanVar(value=True)  # Always on

        ctk.CTkCheckBox(options_frame, text="Случайный порядок", variable=self.random_order_var,
                        command=self._on_random_order_changed).pack(
            anchor="w", padx=20, pady=(6, 2)
        )
        ctk.CTkCheckBox(options_frame, text="Поверх всех окон", variable=self.topmost_var).pack(
            anchor="w", padx=20, pady=(2, 6)
        )

        # Start button is packed at the bottom in _build_ui (at the top of the method)

    def _make_thumbnail(self, path):
        """Generate 48x48 CTkImage thumbnail using Pillow, cache in self.thumbnails."""
        if path in self.thumbnails:
            return self.thumbnails[path]
        try:
            img = Image.open(path)
            img.thumbnail((48, 48))
            # Keep original aspect ratio for thumbnail display
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(img.width, img.height))
            self.thumbnails[path] = ctk_img
            return ctk_img
        except Exception as e:
            log.error(f"Failed to create thumbnail: {path} — {e}")
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
        # Freeze window updates during rebuild
        try:
            self.winfo_toplevel().tk.call("tk", "busy", "hold", self._w)
        except Exception:
            pass
        self.image_list_frame.pack_forget()
        for widget in self.image_list_frame.winfo_children():
            widget.destroy()

        for i, img_data in enumerate(self.images):
            path = img_data["path"]
            bg_color = "#3a3a6a" if i == self.selected_index else None  # None = default
            row = ctk.CTkFrame(self.image_list_frame, fg_color=bg_color)
            row.pack(fill="x", pady=2, padx=2)
            row.img_index = i

            # Number
            ctk.CTkLabel(row, text=f"{i + 1}.", width=25, text_color="gray").pack(side="left", padx=(4, 0))

            # Thumbnail (preserves aspect ratio)
            thumb = self._make_thumbnail(path)
            if thumb is not None:
                thumb_label = ctk.CTkLabel(row, image=thumb, text="")
            else:
                thumb_label = ctk.CTkLabel(row, text="?", width=48, height=48)
            thumb_label.pack(side="left", padx=4, pady=2)
            thumb_label.img_index = i

            # Control buttons (pack right side FIRST so they always show)
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

            # Timer display (pack right side before filename)
            timer_secs = img_data["timer"]
            if timer_secs >= 3600:
                timer_text = f"{timer_secs // 3600}ч {(timer_secs % 3600) // 60}мин"
            elif timer_secs >= 60:
                timer_text = f"{timer_secs // 60} мин"
            else:
                timer_text = f"{timer_secs} сек"
            ctk.CTkLabel(row, text=timer_text, text_color="gray", width=60).pack(side="right", padx=4)

            # Filename label (only if checkbox is on)
            if self.show_filename_var.get():
                filename = os.path.basename(path)
                name_label = ctk.CTkLabel(row, text=filename, anchor="w")
                name_label.pack(side="left", fill="x", expand=True, padx=4)
                name_label.img_index = i
                drag_widgets = (row, thumb_label, name_label)
            else:
                drag_widgets = (row, thumb_label)

            # Click to select + drag-drop bindings
            for widget in drag_widgets:
                widget.bind("<ButtonPress-1>", lambda e, idx=i: self._drag_start(idx, e))
                widget.bind("<B1-Motion>", self._drag_motion)
                widget.bind("<ButtonRelease-1>", self._drag_end)

        # Show filename toggle at bottom of list
        ctk.CTkCheckBox(
            self.image_list_frame, text="Имя файла", variable=self.show_filename_var,
            command=self._on_show_filename_changed,
            checkbox_width=16, checkbox_height=16, font=ctk.CTkFont(size=11)
        ).pack(anchor="w", padx=8, pady=(4, 4))

        # Show frame after rebuild is complete
        if not self._images_collapsed:
            self.image_list_frame.pack(fill="x", padx=10, pady=(0, 5),
                                        after=self._collapse_btn.master)
        # Unfreeze window updates
        try:
            self.winfo_toplevel().tk.call("tk", "busy", "forget", self._w)
        except Exception:
            pass

    def _select_image(self, index):
        self.selected_index = index
        self._refresh_image_list()

    def _on_add_selected(self, choice):
        if choice == "Файлы":
            self._add_files()
        elif choice == "Папка":
            self._add_folder()

    def _clear_images(self):
        """Remove all images from the list."""
        self.images.clear()
        self.thumbnails.clear()
        self.selected_index = None
        self._refresh_image_list()

    def _toggle_image_list(self):
        """Collapse or expand the image list."""
        self._images_collapsed = not self._images_collapsed
        if self._images_collapsed:
            self.image_list_frame.pack_forget()
            self._collapse_btn.configure(text="▶")
        else:
            # Re-pack after header (find header's pack position)
            self.image_list_frame.pack(fill="x", padx=10, pady=(0, 5),
                                        after=self._collapse_btn.master)
            self._collapse_btn.configure(text="▼")

    def _on_random_order_changed(self):
        self.order_var.set("random" if self.random_order_var.get() else "sequential")

    def _on_show_filename_changed(self):
        """Refresh image list to show/hide filenames."""
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

    def _drag_start(self, index, event=None):
        """Record the starting index and position for a drag operation."""
        self.drag_start_index = index
        self._drag_moved = False
        if event:
            self._drag_start_x = event.x_root
            self._drag_start_y = event.y_root

    def _drag_motion(self, event):
        if self._drag_start_x is not None:
            dx = abs(event.x_root - self._drag_start_x)
            dy = abs(event.y_root - self._drag_start_y)
            if dx > 5 or dy > 5:
                self._drag_moved = True

    def _on_preset_selected(self, label):
        """Handle preset dropdown selection."""
        if label == "Своё время...":
            self.custom_row.pack(fill="x", padx=8, pady=(0, 4), after=self._preset_row)
        else:
            self.custom_row.pack_forget()
            seconds = self._preset_map.get(label)
            if seconds is not None:
                self._set_timer(seconds)

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
        try:
            warn_m = int(self.warn_mins_var.get() or 0)
            warn_s = int(self.warn_secs_var.get() or 0)
            warn_secs = warn_m * 60 + warn_s
        except ValueError:
            warn_secs = 10
        settings = {
            "order": self.order_var.get(),
            "fit_window": self.fit_window_var.get(),
            "lock_aspect": self.lock_aspect_var.get(),
            "topmost": self.topmost_var.get(),
            "warn_enabled": self.warn_enabled_var.get(),
            "warn_seconds": max(1, warn_secs),
        }
        log.info(f"Starting refbot: {len(self.images)} images, settings={settings}")
        self.viewer = ViewerWindow(self, self.images, settings)
        self.withdraw()  # Hide settings window

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
        """Complete drag-drop or select image on click."""
        if self.drag_start_index is None:
            return
        # If mouse didn't move much — treat as click (select)
        if not self._drag_moved:
            self._select_image(self.drag_start_index)
            self.drag_start_index = None
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
    log.info("App started")
    app = SettingsWindow()
    app.mainloop()
