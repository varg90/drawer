# Settings Redesign Part 3: Editor Panel + Dock System

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite image_editor_window.py as a dockable editor panel that integrates into the main settings window (right/bottom) or operates as a detached window. Add collapsible groups, file pinning, reserve section, and drop-target list.

**Architecture:** New `ui/editor_panel.py` contains the editor widget (toolbar, file list, grid, controls). `ui/settings_window.py` gains dock management — showing/hiding editor panel in different positions. `ui/image_editor_window.py` becomes a thin wrapper for detached mode.

**Tech Stack:** Python, PyQt6, qtawesome, ui/scales.py, ui/icons.py, ui/theme.py, ui/widgets.py

**Spec:** `docs/superpowers/specs/2026-04-08-settings-redesign.md`

**Depends on:** Plan 1 (foundation) + Plan 2 (main window) — both completed.

---

### Task 1: Create ui/editor_panel.py — core editor widget

**Files:**
- Create: `ui/editor_panel.py`
- Test: `tests/test_editor_panel.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_editor_panel.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ui.editor_panel import EditorPanel


def test_editor_panel_exists():
    assert EditorPanel is not None


def test_editor_panel_is_widget():
    from PyQt6.QtWidgets import QWidget
    assert issubclass(EditorPanel, QWidget)
```

- [ ] **Step 2: Run test — should FAIL**

Run: `python -m pytest tests/test_editor_panel.py -v`

- [ ] **Step 3: Write ui/editor_panel.py**

EditorPanel is a QWidget containing:
- Toolbar: file-plus, folder-plus, link | stretch | detach, eraser, close buttons
- Count label: "IMAGES — N"
- Scrollable file list area (QScrollArea) with dashed border (drop target)
  - Collapsible group headers by timer ("1m — 2", "5m — 3", etc.)
  - File rows: index, pin icon (if pinned), filename, timer
  - Reserve group at bottom for unassigned files
- Bottom controls: list/grid toggle, zoom slider, cache trash + size label
- Total label (red when over budget)

Signals:
- `images_updated = pyqtSignal(list)` — emitted when files change
- `close_requested = pyqtSignal()` — close/dock button clicked
- `detach_requested = pyqtSignal()` — detach button clicked

Constructor: `EditorPanel(images, theme, parent=None, view_mode="list")`

Key methods:
- `refresh(images)` — rebuild file list
- `_build_ui()` — construct layout
- `_apply_theme()` — style with theme colors and S.* sizes
- `_rebuild_list()` — list view with collapsible groups
- `_rebuild_grid()` — grid view with collapsible groups
- `_add_files()`, `_add_folder()`, `_add_from_url()` — file addition
- `_clear()` — clear with confirmation dialog
- `_on_drop()` — handle dropped files (drop target)
- File pinning: right-click context menu or Ctrl+P to pin/unpin file in current group

Use Icons.* for all icon names, S.* for all sizes.

- [ ] **Step 4: Run test — should PASS**

- [ ] **Step 5: Commit**

```bash
git add ui/editor_panel.py tests/test_editor_panel.py
git commit -m "feat: create EditorPanel widget with groups, pinning, reserve"
```

---

### Task 2: Add dock management to settings_window.py

**Files:**
- Modify: `ui/settings_window.py`

- [ ] **Step 1: Add dock state and methods**

Add to SettingsWindow:
- `self._dock_mode = "compact"` — one of: "compact", "right", "bottom", "detached"
- `self._editor_panel = None` — EditorPanel instance

Methods:
- `_open_editor()` — called by + button. If compact → switch to "right" dock. If already docked → do nothing. Creates EditorPanel if needed.
- `_close_editor()` — called by editor close signal. Return to compact mode. Resize window.
- `_detach_editor()` — called by editor detach signal. Open EditorPanel in separate window (ImageEditorWindow wrapper).
- `_dock_editor(position)` — dock editor to right or bottom. Resize main window accordingly.

Window resize rules:
- compact: `setFixedSize(S.MAIN_W, S.MAIN_H)` — 250x270
- right: `setFixedSize(S.MAIN_W + 1 + S.EDITOR_W, S.MAIN_H)` — 501x270
- bottom: `setFixedSize(S.MAIN_W, S.MAIN_H + 1 + editor_h)` — 250x470ish
- detached: main stays at `S.MAIN_W, S.MAIN_H`, editor is separate window

- [ ] **Step 2: Update + button to call _open_editor**

Replace current `_open_editor` (which opens ImageEditorWindow) with new dock-aware version. The + button now opens the docked editor panel instead of a separate window.

- [ ] **Step 3: Add editor panel container to layout**

In `_build_ui`, add a QFrame divider and container widget to the right of main content, initially hidden. When dock mode changes, show/hide and resize.

- [ ] **Step 4: Test dock open/close**

Run: `python -c "from ui.settings_window import SettingsWindow; print('OK')"`

- [ ] **Step 5: Commit**

```bash
git add ui/settings_window.py
git commit -m "feat: add dock management for editor panel"
```

---

### Task 3: Update ImageEditorWindow as detached wrapper

**Files:**
- Modify: `ui/image_editor_window.py`

- [ ] **Step 1: Refactor ImageEditorWindow**

ImageEditorWindow becomes a thin QWidget window that wraps EditorPanel:
- Title bar: "Images" + dock-back button
- Contains EditorPanel as child widget
- dock-back button emits signal to re-dock to main window

Most of the current image_editor_window.py logic moves to editor_panel.py. ImageEditorWindow just:
- Creates EditorPanel
- Adds title bar
- Forwards signals

- [ ] **Step 2: Keep backward compatibility**

SettingsWindow._open_editor can still create ImageEditorWindow for detached mode. The key difference: docked mode uses EditorPanel directly, detached mode uses ImageEditorWindow wrapping EditorPanel.

- [ ] **Step 3: Test**

Run: `python -m pytest tests/ -q`

- [ ] **Step 4: Commit**

```bash
git add ui/image_editor_window.py ui/editor_panel.py
git commit -m "feat: refactor ImageEditorWindow as thin wrapper around EditorPanel"
```

---

### Task 4: File pinning support

**Files:**
- Modify: `core/models.py`
- Modify: `ui/editor_panel.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Add pinned field to ImageItem**

```python
# In core/models.py, add to ImageItem:
pinned: bool = False
```

Update `to_dict()` and `from_dict()` to include pinned state.

- [ ] **Step 2: Write test**

```python
def test_image_item_pinned():
    img = ImageItem(path="test.jpg", timer=300, pinned=True)
    assert img.pinned is True
    d = img.to_dict()
    assert d["pinned"] is True
    restored = ImageItem.from_dict(d)
    assert restored.pinned is True
```

- [ ] **Step 3: Update editor_panel.py**

- Show pin icon next to pinned files (accent color)
- Right-click context menu: "Pin" / "Unpin"
- Pinned files excluded from auto-redistribute

- [ ] **Step 4: Test + commit**

```bash
git add core/models.py ui/editor_panel.py tests/test_models.py
git commit -m "feat: add file pinning support"
```

---

### Task 5: Reserve section and over-budget display

**Files:**
- Modify: `ui/editor_panel.py`
- Modify: `ui/settings_window.py`

- [ ] **Step 1: Reserve group in editor**

Files with timer=0 go to "Reserve" group (inactive style). When adding new files that exceed session time, assign timer=0.

- [ ] **Step 2: Over-budget total display**

In editor panel, show total in red (`theme.warning`) when sum of assigned timers exceeds session duration. Format: "1:07:00 / 1:00:00"

- [ ] **Step 3: Auto-redistribute on settings change**

When user changes session duration or tiers in main window:
1. Recalculate distribution for non-pinned files
2. Try to assign reserve files if time available
3. Update editor panel display

- [ ] **Step 4: Test + commit**

```bash
git add ui/editor_panel.py ui/settings_window.py
git commit -m "feat: add reserve section and over-budget display"
```

---

### Task 6: Session persistence for editor state

**Files:**
- Modify: `ui/settings_window.py`

- [ ] **Step 1: Save/restore dock mode**

Add to `_save_session`:
```python
"view_mode": self._dock_mode,
```

Add to `_restore_session`:
```python
self._dock_mode = data.get("view_mode", "compact")
# Restore dock position on startup if not compact
```

- [ ] **Step 2: Save/restore pinned state**

ImageItem.to_dict/from_dict already handle pinned (Task 4). Session save includes images with pinned state.

- [ ] **Step 3: Test + commit**

```bash
git add ui/settings_window.py
git commit -m "feat: persist editor dock mode and file pinning state"
```

---

### Task 7: Full integration test

- [ ] **Step 1: Run full test suite**

Run: `python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 2: Visual test — launch app**

Run: `python main.py`
- Verify compact window 250x270
- Click + → editor opens docked right (501x270)
- Click close in editor → returns to compact
- Verify theme toggle works in all modes
- Verify Class/Quick mode switch

- [ ] **Step 3: Commit any fixes**

```bash
git add -A
git commit -m "fix: integration fixes for editor panel and dock system"
```

---

## Plan Self-Review

- [x] Spec coverage: editor panel, dock modes, file pinning, reserve, over-budget, persistence — all covered
- [x] Task 1 is largest (editor_panel.py from scratch) — may need splitting if too big
- [x] Backwards compatibility: old ImageEditorWindow still works as detached wrapper
- [x] No hardcoded values — uses S.* and Icons.* throughout
- [x] Pinned state persisted via ImageItem.to_dict/from_dict

## Notes

- Task 1 is the biggest — creating editor_panel.py from scratch. The implementer should reference current image_editor_window.py for existing logic (list rebuild, grid rebuild, flow layout, pixmap loading, etc.) and migrate relevant parts.
- Task 3 strips image_editor_window.py down to a thin wrapper. Most code moves to editor_panel.py in Task 1.
- The dock system (Task 2) is the architectural heart — managing window resize and panel visibility.
