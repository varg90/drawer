# Settings Window Redesign — Design Spec

**Date:** 2026-04-08
**Status:** Approved via mockup iteration

## Overview

Complete redesign of RefBot settings window. Replace current 360px vertical layout with compact 250x270 square-ish design. Integrated editor panel (docked or detached). New icon system, accent theming, unified layout between timer modes.

## Design Decisions

### Window Dimensions
- Main window: **250x270px fixed** — never resizes
- Editor docked right: 250x270 (same height as main)
- Editor docked bottom: 250xN (same width as main)
- Editor detached: free-size, user resizable
- Editor adapts to main window, not the other way around

### Theme System (A+C)
- Dark/Light base palettes with custom accent color
- Default accent: `#4a7d74` (teal)
- `bg_active` = accent-tinted (15% mix for dark, lighten 65% for light)
- `start_text` slightly offset from bg for contrast: `#252525` (dark), `#c4c4c4` (light)
- Accent color picker saved/restored in session
- `scales.json` or equivalent for centralized size system (no more hardcoded px everywhere)

### Header Row
- Info button: **top-left** always (13px icon, no padding)
- Push-pin (always on top): next to info, top-left (13px)
- REFBOT: **always centered** via equal stretch containers
- Accent color dot: top-right (11px circle)
- Theme toggle (moon/sun): top-right (13px)
- All header icons same 13px size, matching REFBOT font-size 11px

### Timer Modes
- Renamed: "Session" → **"Class"**
- Button order: **[Class] [Quick]** — Class first/left
- Both modes use identical layout — zero visual change when switching
- Duration picker `< 1:00:00 >` present in both modes:
  - Class: active (interactive arrows, primary color)
  - Quick: inactive (dimmed arrows, hint color, disabled)
- Timer buttons: same size/style in both modes (`padding: 4px 7px; font-size: 10px`)
- Quick presets: 30s, 1m, 2m, 5m / 10m, 15m, 30m, 1h
- Class tiers: 30s, 1m, 3m, 5m / 10m, 15m, 30m, 1h

### Summary & Total
- Quick: "11 img x 5:00" + "0:55:00"
- Class: "2x1m 3x5m 2x10m" + "0:37:00"
- Both left-aligned, same position
- Single duration number (no "X / Y" in main window — that's editor's job)

### Bottom Bar
- Dice (random order): 34px icon, bottom-left, aligned to left margin
- Start button: 42px, bottom-right, aligned to right margin
- Both bottom-aligned to each other

### Icon Toggles
- Random order ON: `ph.dice-five-fill` (accent color)
- Random order OFF: `ph.dice-three-bold` (hint color)
- Always on top ON: `ph.push-pin-fill` (accent color)
- Always on top OFF: `ph.push-pin-bold` (hint color)

### Start Button
- Icon: `fa6s.pencil`
- Size: 42x42px
- Icon ratio: 0.75 (icon 31px inside 42px button)
- Border radius: 12% of size (~5px)
- Background: accent color
- Icon color: `start_text` (dark bg color in dark mode, light bg color in light mode)
- Rounded square shape

### Margins
- Left/Right/Top: 14px uniform
- Bottom: 18px (slightly larger)
- All elements align to margin edges (info/dice/tiers flush left, accent/moon/start/+ flush right)

### Auto-Distribution
- No "Auto" button — distribution auto-calculates when tiers or duration change
- No "Manual" button — manual editing = open editor panel
- Only non-pinned files are redistributed
- Pinned files stay in their groups

## Editor Panel

### Opening
- `+` button opens editor (wide mode)
- No separate expand button needed
- `X` button in editor closes it (returns to compact)
- Detach button (`ph.arrow-square-out-bold`) opens editor as separate window
- Dock-back button (`ph.arrows-in-bold`) re-attaches to main window

### Dock Modes
- **Right**: editor same height as main (250x270), attached to right edge
- **Bottom**: editor same width as main (250xN), attached to bottom edge
- **Detached**: separate window, free resize, own title bar "Images"
- View mode persisted in session

### File List
- Collapsible groups by timer: "1m — 2", "5m — 3", "10m — 2"
- Click group header to collapse/expand
- Pinned files: push-pin icon + accent color name
- Reserve section: "Reserve — N" (hint color, inactive style)
- Reserve files show "—" instead of timer
- Entire list area is drop target (dashed border)
- Scrollable when content exceeds panel height

### Grid/Tile View
- Same collapsible groups
- Pinned tiles: accent border (2px solid)
- Reserve tiles: dashed hint border
- Zoom slider for tile size (visible in grid mode)

### Toolbar
- Left: file-plus, folder-plus, link (add files/folders/URLs)
- Right: detach, eraser (clear all with confirmation), close
- No separate delete button — Delete key works for selected files

### Bottom Controls
- List/Grid view toggle
- Zoom slider + label (grid mode)
- Cache: trash icon + size label (e.g. "12MB")
- Total time: left-aligned, red when over budget ("1:07:00 / 1:00:00")

### Reserve Behavior
- New files exceeding session time → Reserve
- Reserve has no limit
- When duration/tiers change → auto-redistribute tries to place reserve files
- Reserve files available for manual drag into groups
- Over-budget: total shown in red, no blocking dialog

### File Pinning
- Right-click or dedicated action pins file to current group
- Pinned files: accent-colored name + pin icon
- Auto-redistribute skips pinned files
- Pinned state persisted in session

## Persistence
All state saved/restored via session.json:
- `view_mode`: "compact" | "right" | "bottom" | "detached"
- `timer_mode`: "class" | "quick"
- `accent`: hex color
- `theme`: "dark" | "light"
- `random_order`: bool
- `topmost`: bool
- `timer_seconds`, `session_seconds`, `tiers`
- `editor_view`: "list" | "grid"
- `viewer_size`, `editor_size` (for detached)

## Mockup Files
- `mockup_full.png` — final 4-combo overview (dark/light x class/quick)
- `mockup_square_strip.py` — main window mockup generator
- `mockup_editor.py` — editor panel mockup generator
- `mockup_dock.py` — dock variants mockup generator
- `mockup_075.png` — start button icon reference
