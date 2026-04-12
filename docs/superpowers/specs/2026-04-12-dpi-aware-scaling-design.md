# DPI-Aware Scaling Design

## Problem

The app's main window is fixed at 250x250 logical pixels. On high-resolution screens (macOS Retina, Windows 4K), the window is too small to use comfortably. This blocks sharing the app with anyone who has a different screen than the developer's 1080p display.

Qt6 auto-scales widgets to maintain physical size, but on larger/denser screens users have more screen real estate — "same physical size" feels small. The window occupies 23% of screen height on 1080p but only 17% on 1440p.

## Goal

The app should occupy roughly the same **proportion** of the screen on any display. All UI elements scale uniformly so the layout stays identical at any size.

## Platforms

- Windows (100%, 125%, 150%, 200% system scaling)
- macOS (Retina and non-Retina)

## Approach: Screen-resolution-based scale factor

### Scale factor detection

At startup, before creating windows, read the screen's **logical height** and compute:

```
factor = max(1.0, screen_logical_height / 1080)
```

Capped at 2.0 to avoid extremes. Reference screen is 1080p (the developer's display).

| Screen | Logical height | Factor | Window | % of screen |
|--------|---------------|--------|--------|-------------|
| 1080p (developer) | 1080 | 1.0 | 250px | 23% |
| MacBook 13" | 900 | 1.0 | 250px | 28% |
| MacBook 16" | 1117 | 1.03 | 258px | 23% |
| 27" QHD | 1440 | 1.33 | 333px | 23% |
| 27" 4K @150% | 1440 | 1.33 | 333px | 23% |
| 32" 4K @100% | 2160 | 2.0 | 500px | 23% |

This does NOT conflict with Qt's built-in DPI scaling. Qt handles logical-to-physical pixel mapping (Retina 2x, Windows DPI). We only adjust the logical base size.

### Scaling function

In `ui/scales.py`, a module-level `sc()` function and an `init_scale()` that recomputes all `S` values:

```python
_factor = 1.0

def sc(value):
    """Scale a pixel value by the current factor, rounded to int."""
    return round(value * _factor)

def init_scale(factor):
    """Recompute all S.* constants with the given factor. Call once at startup."""
    global _factor
    _factor = factor
    S.MAIN_W = sc(250)
    S.MAIN_H = sc(250)
    S.MARGIN = sc(14)
    # ... all other constants
```

After `init_scale()`, all existing code reads `S.MARGIN` as before — no call-site changes needed. The `sc()` function is also exported for the few places that build stylesheet strings with inline pixel values (e.g. `f"font-size: {sc(20)}px"`).

### What scales

Every dimension in `scales.py` scales: window size, margins, icon sizes, font pixel sizes, spacing, padding, border radii, button sizes. The window stays square.

### What does NOT change

- Layout structure (which widgets go where)
- Ratios (START_ICON_RATIO, START_RADIUS_RATIO) — these are proportions, not pixels
- Qt's built-in DPI handling — we don't touch it
- Color, theme, font families

## Centralize hardcoded values

60+ hardcoded pixel values scattered across 12 files need to move into `scales.py`. These include:

### viewer_window.py
- CORNER_GRIP = 50, MIN_WIDTH = 200, MIN_HEIGHT = 150, NAV_ZONE = 40
- center_btn: 60x60, alarm/coffee labels: 20x20, progress bar: 3px height
- Font sizes in stylesheets: 20px (timer), 13px (counter), 14px (help)

### editor_panel.py
- GRID_MIN = 48, GRID_MAX = 256, GRID_DEFAULT = 80, ZOOM_STEP = 16
- Scrollbar: 4px width, 20px min-height, 2px radius
- Slider: 4px groove, 12px handle
- Item height: 30px, spacing: 2-5px, borders: 1-2px

### accent_picker.py
- SQ = 120, BAR_W = 12, margins: 10px, spacing: 6-8px, hex input: 20px height

### timer_panel.py
- Mode button height: 28px, padding: 4px 8px

### image_editor_window.py
- EDGE = 6, minimum size: 200x200, spacing: 4-6px

### snap.py
- SNAP_DISTANCE = 15, DETACH_DISTANCE = 40

### bottom_bar.py
- Spacing: 8px

### url_dialog.py
- Multiple padding/font-size values in stylesheets

### Stylesheets generally
- All `font-size: Npx`, `padding: Npx`, `border-radius: Npx`, `border: Npx` in f-strings need to use `sc()` values

## Initialization sequence

1. `QApplication` created
2. `QScreen.availableSize().height()` read (logical pixels, excludes taskbar)
3. `init_scale(max(1.0, min(height / 1080, 2.0)))` called
4. Fonts loaded (sizes now scale via `sc()`)
5. Windows created (all dimensions now scaled)

## Future: user-adjustable scale

Not part of this task. But the design supports it: multiply the auto-detected factor by a user preference (e.g. 0.8x to 1.5x) stored in session.json. The window stays square at any scale.

## Testing

- Verify app looks identical on developer's 1080p screen (factor 1.0)
- Test with manual factor override (1.5, 2.0) to simulate high-res screens
- Verify all elements scale proportionally — no clipping, no overflow
- Run existing test suite (137 tests) to catch regressions
