# Resizable Main Window — Design Spec

## Problem

The main window is fixed at 250x250. Users on different screens (small laptops, 4K monitors) may need the UI bigger or smaller. A separate scale slider would create problems — big UI crammed into a small window doesn't help visibility. The window size itself should be the scale control.

## Solution

Make the main window resizable as a square. Resizing the window scales the entire UI proportionally — fonts, icons, buttons, margins, spacing. The editor matches the main window's scale.

## Behavior

### Main window
- Loses `setFixedSize()`, gets `setMinimumSize(200, 200)` with no maximum
- Aspect ratio locked 1:1 (square) — width always equals height during resize
- Resize grips added (same edge detection + cursor hint system as editor window)
- On mouse release after resize: recalculate scale factor, rebuild UI

### Scale calculation
- Base size: 250px (current `MAIN_W`)
- Scale factor: `window_size / 250`
  - 200px = 0.8x (minimum)
  - 250px = 1.0x (default)
  - 300px = 1.2x
  - 400px = 1.6x
- On resize release: call `init_scale(factor)` to recalculate all `S.*` constants
- DPI factor from system detection is multiplied with user scale — e.g., 2.0x Retina + 300px window = `2.0 * 1.2` = 2.4x effective factor

### Editor sync
- Snapped editor: matches new main window height, width rescales via `S.EDITOR_W`, panel rebuilds with new `S.*` values
- Detached editor: rescales fonts/icons/spacing but keeps user-set position and dimensions
- Closed editor: picks up current scale automatically when next opened

### Viewer
- Not affected. Viewer window size and UI elements stay as they are.

### Session persistence
- Save `window_size` (single integer) in existing session JSON
- On launch: read saved size, calculate factor, call `init_scale(factor)` before building UI
- Default: 250 if no saved size

## Files affected

| File | Change |
|------|--------|
| `ui/scales.py` | `init_scale()` needs to accept combined DPI + user factor |
| `ui/settings_window.py` | Remove `setFixedSize`, add resize handling, square constraint, rebuild on release |
| `ui/image_editor_window.py` | Rebuild on scale change from parent |
| `core/session.py` | Save/load `window_size` |

## Out of scope
- Viewer window scaling
- Separate scale slider or settings UI
- Animation during scale transition
