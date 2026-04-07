# Viewer Redesign — Design Spec

## Summary

Redesign the slideshow viewer UI to layout C6b: minimal overlay controls that appear on hover, large center play/pause, side navigation, full-width progress bar, coffee indicator on pause, and timer that turns red when time is running out.

## Layout

All elements are overlays on top of the image. The window size matches the image — no UI adds to window dimensions.

### Hidden state (cursor outside window)

Depends on play/pause and timer state:

- **Playing, timer normal:** nothing visible — clean image
- **Playing, timer warning:** only red timer text at bottom-left
- **Paused, timer normal:** only coffee icon at bottom-left
- **Paused, timer warning:** coffee icon + red timer text at bottom-left

### Hover state (cursor inside window)

All elements appear with smooth fade-in (~200ms):

**Top area** (gradient fade from black to transparent):
- Left: info button (`ph.info-light`)
- Right: settings (`ph.dots-three-vertical-light`) + close (`ph.x-thin`)

**Center:**
- Playing: large `ph.pause-fill` icon with text shadow
- Paused: large `ph.play-fill` icon with text shadow
- Clicking toggles pause/play

**Sides:**
- Left edge: `ph.caret-left-light` for previous image
- Right edge: `ph.caret-right-light` for next image

**Bottom area:**
- Left: timer text (+ coffee icon when paused), 13px
- Right: counter "3/32", 13px, dimmer
- Full-width progress bar at the very bottom edge (3px height)

## Always-visible elements

These elements are shown regardless of hover state:
- **Coffee icon** (`ph.coffee-light`) — when paused, at bottom-left
- **Red timer** — when in warning zone, at bottom-left (next to coffee if paused)

## Timer + Warning (merged)

The current separate warning overlay (`_warn_label`) is removed. The timer label changes color:
- Normal: `rgba(255,255,255,0.45)` — visible only on hover
- Warning zone: `rgba(255,85,85,0.8)` — visible always, even without hover

When paused AND in warning zone, coffee icon also turns red.

Warning thresholds unchanged (from `core/timer_logic.py`).

## Icons (QtAwesome — Phosphor)

All icons via `qtawesome` library using Phosphor icon sets:

| Element | Icon | Set | Size |
|---------|------|-----|------|
| Info | `ph.info` | light | 15px |
| Settings | `ph.dots-three-vertical` | light | 15px |
| Close | `ph.x` | thin | 15px |
| Pause (center) | `ph.pause` | fill | 40px |
| Play (center) | `ph.play` | fill | 40px |
| Previous | `ph.caret-left` | light | 22px |
| Next | `ph.caret-right` | light | 22px |
| Coffee (pause) | `ph.coffee` | light | 15px |

Icon rendering: `qtawesome.icon("ph.pause", color=QColor(...))` → QIcon/QPixmap.

## Progress bar

- Position: absolute bottom, full width, no margins
- Height: 3px
- Background: `rgba(255,255,255,0.08)`
- Fill: `rgba(255,255,255,0.35)` (normal) / `rgba(255,85,85,0.8)` (warning)
- Shows elapsed time as percentage of current image timer

## Animations

- Hover in: all overlay elements fade in (~200ms)
- Hover out: all overlay elements fade out (~200ms)
- Exceptions that stay visible: coffee icon (when paused), red timer (when warning)

## Controls behavior

- **Click center area** → toggle pause/play
- **Click left edge** → previous image
- **Click right edge** → next image
- **F11** → toggle fullscreen (no button, keyboard only)
- **Keyboard shortcuts** unchanged: Space, Left/Right, F11, Esc, H

## What changes

- Remove `IconButton` class (replaced by QtAwesome icons)
- Remove `_warn_label` (merged into timer)
- Remove `_controls_bar` widget (bottom nav bar)
- Remove `_help_container` widget
- Remove fullscreen button (F11 only)
- Rebuild top buttons with QtAwesome Phosphor icons
- Add center play/pause (large, fill style)
- Add left/right navigation zones with caret icons
- Add progress bar (3px, full width)
- Add coffee indicator for pause state
- Add fade animation via QPropertyAnimation on opacity

## What stays the same

- Window flags (frameless, optional topmost)
- Resize from edges/corners
- Right-click drag to move
- Keyboard shortcuts
- Image loading and display logic
- Timer tick logic and warning thresholds
- Session size persistence
