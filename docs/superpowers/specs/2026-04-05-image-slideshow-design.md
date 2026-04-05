# Image Slideshow — Design Spec

## Overview

Desktop application for displaying a slideshow of user-loaded images with configurable timers, always-on-top mode, and flexible display order. Built with Python + CustomTkinter.

## Architecture

Single-file application (`main.py`) with a JSON config file (`session.json`) for session persistence.

Two windows:
1. **Viewer window** — displays the current image
2. **Settings window** — controls and configuration

## Viewer Window

- Displays the current image fullscreen within the window
- **Default behavior:** window resizes to match the image aspect ratio
- **Fixed size mode:** image scales to fit inside the window (preserving aspect ratio, with letterboxing if needed)
- Resizable by the user at any time
- Dark background (#1a1a2e or similar)

### Hover Controls

Appear on mouse hover, hidden otherwise:

- **Navigation buttons:** previous, pause/play, next (centered bottom, semi-transparent bar)
- **Image counter:** "3 / 12" (top-right corner)

## Settings Window

Opens as a separate window. Contains all controls:

### Image List

- Scrollable list of loaded images
- Each item shows: thumbnail (48x48), filename, timer value (in individual mode)
- Controls per item: move up, move down, delete
- Drag-and-drop reordering: hold and drag an item to change its position in the list
- Buttons at top: "Add Files", "Add Folder"
- Supported formats: JPG, JPEG, PNG, GIF, BMP, WEBP

### Timer Mode

Toggle between two modes:

1. **Uniform** — one timer for all images
2. **Individual** — each image has its own timer (editable in the image list)

### Timer Selection

Quick-select buttons: 1 min, 5 min, 10 min, 15 min, 30 min, 1 hour

Custom input: three fields (hours, minutes, seconds) + OK button
- Range: 1 second to 3 hours
- Validation: reject values outside this range

In **individual mode**, the timer selection applies to the currently selected image in the list. If no image is selected, the timer applies to all images that haven't been individually configured yet (acts as a default).

### Display Order

Toggle between:
- **Sequential** — follow list order
- **Random** — shuffle on each cycle

### Options (Checkboxes)

- **Always on top** — viewer window stays above all other windows
- **Loop** — restart from beginning after last image (when off, stop on last image)
- **Fit window to image** — window resizes to match image proportions (when off, fixed window size with image scaled to fit)
- **Lock aspect ratio** — preserve window proportions when resizing manually (scales both width and height together)

### Start Button

Launches the slideshow in the viewer window.

## Session Persistence

### Save (on app close)

Write to `session.json` in the app directory:
- List of image paths
- Timer mode and values (uniform value + individual values)
- Display order setting
- Checkbox states (always on top, loop, fit window)
- Window position and size

### Restore (on app start)

If `session.json` exists, show dialog: "Restore previous session?" with Yes/No buttons.
- **Yes:** load all settings and image list from file
- **No:** start fresh, empty state

## File Structure

```
C:\Users\Ellie\sandbox\
├── main.py          # Application entry point, all code
├── session.json     # Saved session (auto-created)
└── CLAUDE.md        # Project info
```

## Dependencies

- `customtkinter` — UI framework (installed)
- `Pillow` — image loading and thumbnails (needs install via `python -m pip install Pillow`)
- `tkinter` — file dialogs, built into Python

## Technical Notes

- Use `CTkToplevel` for the viewer window, `CTk` for settings
- Always-on-top via `wm_attributes('-topmost', True/False)`
- Image display via `CTkLabel` with `CTkImage`
- Thumbnails generated with `Pillow` (`Image.thumbnail()`)
- Timer via `root.after()` for non-blocking delays
- File dialogs via `tkinter.filedialog.askopenfilenames` and `askdirectory`
- Session file: standard `json.dump` / `json.load`
