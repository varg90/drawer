# Session Limit Redesign

## Problem

Duration picker (stepper) takes a full row for a secondary feature. Class mode tangles two concerns: distributing images across tiers and capping session time. When images exceed session time, overflow images get timer=0 — broken.

## Solution

Separate tier distribution from session time limit. Tiers assign timers to ALL images (no overflow). Session limit is an independent countdown that ends the slideshow when time's up.

## UI Changes

### Remove duration picker stepper

Delete the `< 45:00 >` stepper row (arrows + large centered label). Remove associated scales: `DURATION_ARROW`, `DURATION_ARROW_BTN`, `FONT_DURATION`, `SPACING_DURATION`.

### New summary line (class mode)

Line 1: group breakdown — `3x30s  2x1m  3x5m  2x30m`
Line 2: total + limit — `1:17:30 · no limit` or `1:17:30 · limit: 45m`

- Total time = sum of all image timers after tier distribution
- Limit label: accent color when active, hint color when "no limit"
- Left-click cycles forward: off → 5m → 10m → 15m → 30m → 45m → 1h → 1.5h → 2h → 3h → off
- Right-click cycles back
- Tooltip: "Session time limit"
- When limit is off: show `no limit` in hint color
- When limit is set: show `limit: Xm` in accent color, underlined

### Quick mode summary (unchanged)

`10 images` + `50:00` — no limit control shown in quick mode.

## Behavior Changes

### Tier distribution

`_auto_distribute` assigns ALL images to tiers. No overflow — if more images than tiers can fit evenly, last tier absorbs extras. Every image gets a real timer > 0.

### Session limit in viewer

- `ViewerWindow` receives optional `session_limit` in settings dict (seconds or None)
- Viewer tracks `_session_elapsed` — incremented each tick alongside per-image countdown
- When `_session_elapsed >= session_limit`, slideshow ends via `_finish()`
- Per-image timer still controls individual image advancement as before
- Session limit is independent — if all images finish before limit, slideshow ends normally

### Session limit display in viewer

- When session limit is active, show remaining session time next to the coffee icon area at bottom-left
- Format: `[session remaining]` in dim text, e.g. `32:15`
- Warning color when < 5 minutes remaining
- Not shown when limit is off

## Data Flow

### Settings → Viewer

```python
settings = {
    "order": "sequential",
    "topmost": self._topmost,
    "viewer_size": ...,
    "session_limit": self._session_limit,  # seconds or None
}
```

### Session save/restore

```json
{
    "session_limit": 2700,
    ...
}
```

`session_limit: null` or absent = no limit.

## Constants

### New: SESSION_LIMIT_PRESETS

```python
SESSION_LIMIT_PRESETS = [
    (None, "no limit"),
    (300, "5m"),
    (600, "10m"),
    (900, "15m"),
    (1800, "30m"),
    (2700, "45m"),
    (3600, "1h"),
    (5400, "1.5h"),
    (7200, "2h"),
    (10800, "3h"),
]
```

### Remove: SESSION_PRESETS

Old `SESSION_PRESETS` replaced by `SESSION_LIMIT_PRESETS`.

### Remove from scales

- `DURATION_ARROW`
- `DURATION_ARROW_BTN`
- `FONT_DURATION`
- `SPACING_DURATION`

## Files Changed

| File | Change |
|------|--------|
| `core/constants.py` | Replace `SESSION_PRESETS` with `SESSION_LIMIT_PRESETS` |
| `ui/scales.py` | Remove duration picker scales |
| `ui/settings_window.py` | Remove stepper UI, add clickable limit label in summary, rework `_auto_distribute` to cover all images, pass `session_limit` to viewer |
| `ui/viewer_window.py` | Track session elapsed, end on limit, show session remaining |
| `core/class_mode.py` | Ensure distribution covers all images (no overflow) |
| `tests/` | Update affected tests |
