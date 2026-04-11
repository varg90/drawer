# Drawer — Sketchbook Redesign

**Date:** 2026-04-11
**Status:** Approved
**Mockup:** `redesign_concept.html` (project root)

## Overview

Complete visual redesign of the Drawer app with a "Sketchbook / Artist's Studio" aesthetic. The app should feel like it's made from physical art materials — paper, wood, leather, ink — not screens. Every design choice references the artist's workflow.

## Fonts

| Font | Weight | Usage | Size |
|------|--------|-------|------|
| Lora | 700 | Title "Drawer", viewer countdown | 17px title, 20px countdown |
| Lexend | 300-500 | Everything else | 9-13px per context |

- Bundle as .ttf files in project
- Load via `QFontDatabase.addApplicationFont()`
- Check return value, log warning on failure
- ~120KB total bundle

## Color Palette

### Dark — "Ink & Coffee"

| Token | Value | Usage |
|-------|-------|-------|
| bg | `#16120e` | Window background (with gradient) |
| bg_panel | `#120e0a` | Inset panel background |
| bg_button | `#16120e` | Inactive buttons (match window bg) |
| border | `#120e0a` | All window outlines, spine between snapped windows |
| text_primary | `#ccc0ae` | Main text |
| text_secondary | `#7a6b5a` | Secondary text |
| text_hint | `#4a3e32` | Hint/disabled text |
| text_header | `#6b5e4e` | Title (with emboss text-shadow) |
| start_text | `#16120e` | Pencil icon on start button (matches window bg) |
| accent | `#4a7d74` | User-selectable, default teal |
| active_bg | `#4a7d74` | Active buttons/tabs fill |
| active_text | `#120e0a` | Text on active buttons |
| warning | `#cc5555` | May need adjustment for warm bg — test |

### Light — "Craft Paper"

| Token | Value | Usage |
|-------|-------|-------|
| bg | `#d8ccb8` | Window background |
| bg_panel | `#c8bca4` | Inset panel (darker than window) |
| bg_button | `#d8ccb8` | Inactive buttons (match window bg) |
| border | `#c0b4a0` | Window outlines |
| text_primary | `#2a2018` | Main text |
| text_secondary | `#5a5248` | Secondary text |
| text_hint | `#a0947e` | Hint/disabled text |
| text_header | `#7a6e5e` | Title (with light emboss) |
| start_text | `#d8ccb8` | Pencil icon (matches window bg) |
| active_text | `#f0ebe2` | Text on active buttons |

## Background Gradients (Sketchbook Effect)

When main + editor are side by side, each window gets a gradient that's lighter toward the shared "spine" — like an open book lit from above.

| Window | Dark | Light |
|--------|------|-------|
| Main | `gradient(to right, #12100c, #1c1814)` | Solid `#d8ccb8` |
| Editor | `gradient(to left, #12100c, #1c1814)` | Solid `#e0d6c4` |

QSS: `qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #12100c, stop:1 #1c1814)`

Child widgets must set own background explicitly to avoid inheriting gradient.

## Rounded Corners

### Implementation

```python
self.setAttribute(Qt.WA_TranslucentBackground)

def paintEvent(self, event):
    painter = QPainter(self)
    painter.setRenderHint(QPainter.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(QRectF(self.rect()), 8, 8)
    painter.fillPath(path, bg_color)
```

Works on Win10 (DWM always on since Win8). Confirmed on user's system (Win10 Home 10.0.19045).

### Rounding Scale

| Radius | Elements |
|--------|----------|
| 3px | Editor list items |
| 5px | Timer buttons, mode tabs, add button |
| 6px | Inset panel |
| 8px | Windows, viewer |
| 10px | Start button |

### Snap-Dependent Rounding

| State | Main window | Editor window |
|-------|-------------|---------------|
| Snapped | `8px 0 0 8px` (left only) | `0 8px 8px 0` (right only) |
| Detached | `8px` (all) | `8px` (all) |
| Standalone | `8px` (all) | N/A |

## Layout

### Main Window (250x250)

```
12px top padding
[info] [palette*] [moon]    Drawer    [pin] [-] [x]    ← header, 22px

          margin-top: auto (air)

    ┌─────────────────────────────────┐
    │  [class] [quick]                │  ← panel, 6px padding
    │  [30s][1m][3m][5m]              │    mode tabs 28px, 4px gap
    │  [10m][15m][30m][1h]            │    timer grid 30px, 4px gap
    └─────────────────────────────────┘

          margin-bottom: auto (air)

12 images
36:00 · no limit              [+] [pencil]    ← bottom bar
14px bottom padding
```

- Panel: bg color difference + inner shadow (no border)
- Panel centered vertically via auto margins
- Presets: 30s, 1m, 3m, 5m | 10m, 15m, 30m, 1h
- Start button: 52x52px, 10px radius, FA pencil icon
- Add button: 26x26px, 5px radius
- Session limit: clickable, cycles presets

### Editor Window (250x250 min)

```
12px top padding (matches main)
[add-file] [add-folder] [link]              [x]    ← toolbar, 14px side padding

    ┌── 1m · 4 ──────────────────┐
    │ [pin][pin][tile][tile]      │    ← grid tiles, 4-col
    ├── 5m · 2 ──────────────────┤
    │ [tile][tile]                │
    ├── 15m · 1 ─────────────────┤
    │ [tile]                      │
    └─────────────────────────────┘

          margin-top: auto (push to bottom)

[list][grid] | [-zoom][+zoom] | [shuffle]    [trash] 1.2MB | [eraser]
14px bottom padding (matches main)
```

- NO detach/dock button
- Pinned tiles: small ph-fill push-pin icon, 8px, top-right corner
- Pinned images sort to top of their group
- Zoom: Ctrl+scroll primary, magnifying-glass -/+ buttons visible
- Bottom bar aligns with main window bottom bar
- Grid tiles grouped by timer tier with collapsible headers

### Viewer

```
┌────────────────────────────────────────────────────────┐  8px radius
│ [info]        [bw][grid][flipH][flipV]      [...][x]  │
│                                                         │
│                       [pause]                           │  center only
│                                                         │
│ [alarm][coffee]        1:47              3/10           │
│ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │  3px progress
└────────────────────────────────────────────────────────┘
```

- ONE countdown only (bottom center, Lora serif 20px)
- Play/pause: center, 56px area (the ONLY center element)
- Warm brown gradient overlays: `rgba(18,14,10,.88)` (not pure black)
- Works in both horizontal and vertical orientations
- Bottom: alarm + coffee (left), countdown (center), counter (right)

## Start Button

52x52px, 10px border-radius, FA pencil icon matching window bg color.

Four styles explored in mockup (user to pick):
1. **Solid** — flat accent fill
2. **Outlined** — accent border, fills on hover
3. **Warm glow** — accent fill + teal shadow
4. **Tactile** — gradient top-to-bottom, presses on click

## Active States

- Timer buttons + mode tabs: full accent fill when active
- Class mode: multiple tiers simultaneously active
- Start button: accent fill always

## Behavioral Changes

- Pinned images sort to top of their group (before unpinned)
- Zoom slider replaced with Ctrl+scroll + magnifying glass +/- buttons
- Editor bottom bar reorganized: view toggles + zoom + shuffle (left), cache + clear (right)

## Removed Elements

- Accent bar (top edge decoration)
- Drawer handle
- Detach/dock button in editor
- Zoom slider

## Implementation Notes

- Panel inner shadow: skip in v1, just bg color. Add QPainter shadow later if flat.
- `#cc5555` warning color may need brightening on warm browns — test.
- Gradients: QSS `qlineargradient()` is cross-platform, zero risk.
- Fonts: `QFontDatabase.addApplicationFont()` is cross-platform.
- Rounded windows: `WA_TranslucentBackground` + QPainter is universal.
- Embossed title: `text-shadow` equivalent via QPainter drawText with offset.
