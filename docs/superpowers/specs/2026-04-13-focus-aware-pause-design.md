# Focus-Aware Pause

## Overview

Drawer watches an external drawing app chosen by the user. When that app loses focus (minimized or user switches away), Drawer's timer auto-pauses. There is no auto-resume — the user resumes manually when ready.

Inspired by the Work timer utility (`C:\!!Work\+\Plugins\work`), which tracks up to 3 programs and changes color based on their focus state.

## UI

### Placement

Replaces the groups distribution text in the settings window. Sits in the same row as the add/start buttons, on the left side — directly above the total time + limit line.

### Toggle

Icon-style button matching the existing pin/theme button style (not a checkbox). Two states:

- **Off:** `[toggle] Pause with app` — app selector hidden
- **On:** `[toggle] Pause with: [Photoshop x]` — app selector visible

### App Selector Button

5 saved slots that cycle like the session limit button:

- **Left click** — next slot
- **Right click** — previous slot
- **Filled slot** — shows app name + **x** button (click x to clear the slot)
- **Empty slot** — shows "Select" + **arrow** button (click arrow to open running apps dropdown)
- Cycles through all 5 slots in a full circle

### Running Apps Dropdown

Opens when clicking the arrow on an empty slot:

- Lists all currently running windowed applications
- Maximum 8-10 visible items before scrolling
- Selecting an app fills the current slot and saves it

## Behavior

### Pause Logic

- When the tracked external app loses focus (window deactivate / minimize), Drawer's timer auto-pauses
- No auto-resume — user must manually resume (spacebar or play button in viewer)
- If the user has already manually paused, focus loss does not change anything
- Only one app is actively tracked at a time (whichever slot is currently selected)

### Persistence

All state saved in `session.json` between sessions:

- Toggle on/off state
- Currently selected slot
- All saved apps across all 5 slots

## Groups Text Removal

The groups distribution text ("4x30s 4x1m 4x3m...") is removed from the settings window. This information is redundant — the editor already shows group names with timestamps and image counts.

## Technical Notes

### Window Focus Detection

- On Windows: poll `GetForegroundWindow()` via ctypes, or use Qt's `QWindow` / platform events
- Match tracked app by process name or window class name
- Polling interval: ~500ms–1s (lightweight, no performance concern)

### App Discovery

- Enumerate visible top-level windows with titles
- Filter out system/shell windows (taskbar, desktop, system tray)
- Display the application name (not window title) where possible
