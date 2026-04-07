# Viewer Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the slideshow viewer UI with Phosphor icons via QtAwesome, overlay controls on hover, progress bar, and coffee pause indicator.

**Architecture:** Single-file rewrite of `ui/viewer_window.py`. Remove `IconButton` class, replace with QtAwesome Phosphor icons on QPushButton. Restructure overlays: gradient top bar, center play/pause, side carets, bottom timer/counter/progress. Add fade animation and always-visible elements (coffee, red timer).

**Tech Stack:** PyQt6, qtawesome (Phosphor icons), QPropertyAnimation

**Spec:** `docs/superpowers/specs/2026-04-07-viewer-redesign-design.md`

---

### Task 1: Rewrite viewer_window.py

**Files:**
- Rewrite: `ui/viewer_window.py`

Since this is a complete UI rewrite of a single file with tightly coupled components, it's implemented as one task.

- [ ] **Step 1: Rewrite the entire viewer_window.py**

The new file replaces everything. Key changes:
- Remove `IconButton` class entirely
- Use `qtawesome.icon()` for all icons (Phosphor sets)
- New overlay structure: top gradient bar, center play/pause, side carets, bottom timer/counter/progress
- Fade in/out on hover via QGraphicsOpacityEffect + QPropertyAnimation
- Always-visible: coffee icon (paused) and red timer (warning)
- Progress bar as QWidget painted manually
- No fullscreen button (F11 only)

- [ ] **Step 2: Verify import works**

Run: `python -c "from ui.viewer_window import ViewerWindow; print('OK')"`

- [ ] **Step 3: Run full test suite**

Run: `python -m pytest tests/ -v`
Expected: all PASS (no viewer tests exist, but no regressions)

- [ ] **Step 4: Manual test**

Run: `python main.py`
1. Load images, start slideshow
2. Verify hover shows all controls with Phosphor icons
3. Verify controls hide when cursor leaves
4. Verify center click toggles pause/play
5. Verify coffee icon appears when paused (always visible)
6. Verify side carets navigate images
7. Verify timer turns red in warning zone and stays visible without hover
8. Verify progress bar fills and turns red in warning zone
9. Verify F11 toggles fullscreen
10. Verify keyboard shortcuts work
11. Verify resize from edges works
12. Verify settings button opens settings without closing viewer

- [ ] **Step 5: Commit**

```bash
git add ui/viewer_window.py
git commit -m "feat: redesign viewer UI — Phosphor icons, overlay controls, progress bar"
```
