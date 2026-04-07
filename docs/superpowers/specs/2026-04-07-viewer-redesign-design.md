# Viewer Redesign — Design Spec

## Summary

Redesign the slideshow viewer UI to layout C6b: minimal overlay controls that appear on hover, large center play/pause, side navigation, full-width progress bar, and timer that turns red and stays visible when time is running out.

## Layout

All elements are overlays on top of the image. The window size matches the image — no UI adds to window dimensions.

### Hidden state (cursor outside window)
- Only the image is visible
- Exception: when timer is in warning zone, the timer text is shown (red, with text shadow) at bottom-left

### Hover state (cursor inside window)
All elements appear with smooth fade-in:

**Top area** (gradient fade from black):
- Left: help button (?)
- Right: fullscreen, settings (hamburger), close (x)

**Center:**
- Large pause/play icon (no circle background), with text shadow
- Clicking toggles pause/play

**Sides:**
- Left edge: chevron-left for previous image
- Right edge: chevron-right for next image

**Bottom area:**
- Timer text at bottom-left (above progress bar)
- Counter (e.g. "3/32") at bottom-right (above progress bar)
- Full-width progress bar at the very bottom edge of the window (3px height)

## Timer + Warning (merged)

The current separate warning overlay (`_warn_label`) is removed. Instead, the timer label itself changes color:
- Normal: `rgba(255,255,255,0.35)` — visible only on hover
- Warning zone (existing thresholds from `auto_warn_seconds`): red color `#ff5555` — visible always, even without hover

The warning thresholds remain unchanged (defined in `core/timer_logic.py`).

## Icons

All icons use QtAwesome (Font Awesome 5 Solid set):
- `fa5s.question-circle` — help
- `fa5s.expand` — fullscreen
- `fa5s.compress` — exit fullscreen  
- `fa5s.bars` — settings/menu
- `fa5s.times` — close
- `fa5s.pause` — pause (center, large)
- `fa5s.play` — play (center, large)
- `fa5s.chevron-left` — previous
- `fa5s.chevron-right` — next

Icon rendering: `qtawesome.icon("fa5s.pause", color=QColor(...))` produces QIcon/QPixmap at any size.

## Animations

- Hover in: all overlay elements fade in (~200ms)
- Hover out: all overlay elements fade out (~200ms)
- Exception: timer in warning state stays visible (no fade out)

## Controls behavior

- **Click center area** → toggle pause/play
- **Click left edge** → previous image
- **Click right edge** → next image
- **Keyboard shortcuts** unchanged: Space, Left/Right, F11, Esc, ?, H

## Progress bar

- Position: absolute bottom, full width, no margins
- Height: 3px
- Background: `rgba(255,255,255,0.08)`
- Fill: `rgba(255,255,255,0.35)` (normal) / `#ff5555` (warning zone)
- Shows elapsed time as percentage of current image timer

## What changes

- Remove `IconButton` class (replaced by QtAwesome QIcon on QPushButton)
- Remove `_warn_label` (merged into timer)
- Remove `_controls_bar` widget (bottom nav bar with prev/pause/next)
- Remove `_help_container` widget
- Rebuild `_top_buttons` with QtAwesome icons
- Add center play/pause button (large)
- Add left/right navigation zones
- Add progress bar widget
- Add fade animation via QPropertyAnimation on opacity

## What stays the same

- Window flags (frameless, optional topmost)
- Resize from edges/corners
- Right-click drag to move
- Keyboard shortcuts
- Image loading and display logic
- Timer tick logic
- Session size persistence
