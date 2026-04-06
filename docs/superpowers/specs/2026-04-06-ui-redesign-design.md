# RefBot UI Redesign — Design Spec

## Goal

Redesign the settings window and image editor for a minimal, distraction-free look. Grey color scheme, sharp corners, no emojis. Keep all existing functionality.

## Visual Style

- Background: dark grey (#1c1c1c)
- Text: light grey (#ccc) for primary, (#555) for secondary, (#444) for hints
- Borders: 1px solid #333 or #444
- No border-radius anywhere (sharp corners throughout)
- Font: system default (Segoe UI on Windows)
- Labels: uppercase, letter-spacing 2-3px, 9px, #555
- No emojis — text only, symbols like `<` `>` `x` `^` `v` for controls

## Settings Window (Main)

Single compact vertical card layout. No scroll needed. Top to bottom:

### 1. Header
- "REFBOT" centered, uppercase, letter-spacing 3px, #777, 11px

### 2. Drop Zone
- Full-width rectangle, 1px dashed border #444, background #1a1a1a
- Text: "Перетащите изображения сюда" (#555, 12px)
- Subtext: "или нажмите для выбора" (#444, 10px)
- Clicking opens file dialog (same as current add-files)
- Drag-and-drop from Explorer (existing functionality)

### 3. Thumbnail Strip
- Horizontal row of square thumbnails (36x36px), 2px gap, no border-radius
- Background #2a2a2a for each
- If more than fit in row, last thumbnail shows "+N" count
- "Edit" button (9px, border 1px solid #333, padding 3px 6px) on the right — opens Image Editor Window

### 4. Timer Mode Switch
- Two-segment toggle, full-width, 1px border #333
- Active segment: background #333, text #ccc
- Inactive segment: background #1c1c1c, text #555
- Labels: "Стандартный" and "Сеанс"

### 5a. Standard Mode Content
- Timer value: large centered text (30px, font-weight 300, #ccc)
- Left/right arrows (`<` `>`) to cycle through presets
- Quick preset buttons below: 1м, 5м, 10м, 15м, 30м
  - Active: background #333, border #444, text #ccc
  - Inactive: background #252525, border #333, text #666
- Presets correspond to TIMER_PRESETS from constants.py (60, 300, 600, 900, 1800 seconds)

### 5b. Session Mode Content
Replaces standard content when "Сеанс" is active:

- Label "ДЛИТЕЛЬНОСТЬ СЕАНСА" centered (uppercase, 9px, #555, letter-spacing 2px)
- Duration value with arrows, same style as standard timer (30px, `<` `>`)
  - Cycles through SESSION_PRESETS: 10м, 30м, 1ч, 1.5ч, 2ч, 3ч
- Label "ИСПОЛЬЗОВАТЬ" centered (uppercase, 9px, #555)
- Tier toggle buttons (30с, 1м, 3м, 5м, 10м, 15м, 30м, 1ч)
  - Same active/inactive style as presets
  - Clicking toggles on/off — determines which durations auto-distribute uses
- "Авто-распределение" button centered (background #252525, border #333, 10px, #777)
- Result line: compact inline text, e.g. "5x30с  5x1м  3x3м  3x5м" (centered, #666, 10px)

### 6. Random Order Checkbox
- Small checkbox (10x10px, border 1px solid #444, sharp corners) + label "Случайный порядок" (9px, #555)
- Centered

### 7. Summary Line
- Centered, #555, 11px
- Standard mode: "16 изображений / 1:20:00"
- Session mode: "16 из 16 изображений / 57:30 из 1:00:00"

### 8. Always-on-Top Checkbox
- Same style as random checkbox, left-aligned
- Label: "Поверх всех окон" (9px, #555)

### 9. Start Button
- Full-width, background #555, text #eee
- Uppercase, letter-spacing 1px, 13px, font-weight 500
- Padding 11px vertical

## Image Editor Window

Separate window, opened by "Edit" button on thumbnail strip.

### Header Row
- Left: "Изображения — N" (#999, 11px)
- Right: close button "x" (#555, 12px)

### Toolbar Row
- Buttons: "+ Файлы", "+ Папка" (left), "Очистить" (right)
- Style: background #252525, border 1px solid #333, 9px, #777

### File List
- Scrollable list, alternating row backgrounds (#222 / #282828)
- Each row: number (9px, #555, 14px wide) | thumbnail (28x28) | filename (10px, #999, flex) | timer (9px, #555) | delete "x" (10px, #444)
- Selected row: border 1px solid #555, filename text #ccc
- Drag-and-drop reordering supported
- Multi-select supported (existing behavior)

### Bottom Controls
- Centered up/down arrows: "^" and "v" buttons
- Style: background #252525, border 1px solid #333, 10px, #777

## Viewer Window

No changes to the viewer window (frameless image display with hover controls). Keep current implementation as-is.

## Behavior Notes

- All existing functionality preserved: drag-and-drop files onto main window, session save/restore, class mode auto-distribution, manual group editing
- Auto-distribute assigns groups sorted ascending by timer — first images get shortest timers, last images get longest
- Random order only applies when checkbox is checked (shuffles at slideshow start, not during distribution)
- Summary line updates dynamically when images or timer settings change
- Session is saved on close, restored on open (existing behavior)
- Thumbnail strip shows first N images that fit + overflow counter

## Architecture

- Keep existing core/ module unchanged (models, constants, timer_logic, class_mode, file_utils, session)
- Rewrite ui/settings_window.py with new layout and styling
- Create ui/image_editor_window.py for the separate editor window
- Keep ui/viewer_window.py unchanged
- Update ui/image_list_widget.py if needed for the new editor context
