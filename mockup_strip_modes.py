"""Strip layout: Quick + Session modes, icon toggles, start lower-right."""
import sys
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                              QLabel, QPushButton, QFrame, QListWidget, QListWidgetItem)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QPixmap, QPainter, QColor
import qtawesome as qta

ICON = "fa6s.pencil"
ICON_RATIO = 0.75
RADIUS_RATIO = 0.12

DARK = {
    "bg": "#191919", "bg2": "#171717", "btn": "#222222",
    "active": "#333b3a", "border": "#303030", "accent": "#4a7d74",
    "primary": "#ddd", "secondary": "#606060", "hint": "#454545",
    "header": "#84a39e", "btn_text": "#84a39e", "start_text": "#252525",
}


def _start_btn(t, size=36):
    btn = QPushButton()
    icon_sz = int(size * ICON_RATIO)
    radius = int(size * RADIUS_RATIO)
    btn.setIcon(qta.icon(ICON, color=t["start_text"]))
    btn.setIconSize(QSize(icon_sz, icon_sz))
    btn.setFixedSize(size, size)
    btn.setStyleSheet(
        f"background-color: {t['accent']}; border: none; border-radius: {radius}px;")
    return btn


def _icon_toggle(t, icon_on, icon_off, is_on, size=20):
    btn = QPushButton()
    icon_name = icon_on if is_on else icon_off
    color = t["accent"] if is_on else t["hint"]
    btn.setIcon(qta.icon(icon_name, color=color))
    btn.setIconSize(QSize(size - 4, size - 4))
    btn.setFixedSize(size, size)
    btn.setStyleSheet("background: transparent; border: none;")
    return btn


def _sep_h(t):
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet(f"color: {t['border']};")
    line.setFixedHeight(1)
    return line


def _mode_toggle(t, active="quick"):
    row = QHBoxLayout()
    row.setSpacing(0)
    for lb, key in [("Quick", "quick"), ("Session", "session")]:
        b = QPushButton(lb)
        is_active = key == active
        s = t['active'] if is_active else t['bg']
        c = t['primary'] if is_active else t['secondary']
        b.setStyleSheet(
            f"background-color: {s}; color: {c}; "
            f"border: 1px solid {t['border']}; font-size: 9px; padding: 3px 6px;")
        row.addWidget(b)
    return row


def _editor_panel(t):
    panel = QWidget()
    pl = QVBoxLayout(panel)
    pl.setContentsMargins(8, 6, 8, 6)
    pl.setSpacing(4)

    tb = QHBoxLayout()
    tb.setSpacing(4)
    for icon_name in ["ph.file-plus-bold", "ph.folder-plus-bold", "ph.link-bold"]:
        b = QPushButton()
        b.setIcon(qta.icon(icon_name, color=t["btn_text"]))
        b.setIconSize(QSize(12, 12))
        b.setFixedSize(22, 20)
        b.setStyleSheet(f"background-color: {t['btn']}; border: 1px solid {t['border']};")
        tb.addWidget(b)
    tb.addStretch()
    eraser = QPushButton()
    eraser.setIcon(qta.icon("ph.eraser-bold", color=t["btn_text"]))
    eraser.setIconSize(QSize(12, 12))
    eraser.setFixedSize(22, 20)
    eraser.setStyleSheet(f"background-color: {t['btn']}; border: 1px solid {t['border']};")
    tb.addWidget(eraser)
    pl.addLayout(tb)

    count = QLabel("IMAGES — 12")
    count.setStyleSheet(f"color: {t['secondary']}; font-size: 9px; font-weight: 500; letter-spacing: 1px;")
    pl.addWidget(count)

    lw = QListWidget()
    lw.setStyleSheet(
        f"QListWidget {{ background-color: {t['bg2']}; border: none; "
        f"font-size: 10px; color: {t['primary']}; }}"
        f"QListWidget::item {{ padding: 2px; }}")
    for i in range(8):
        lw.addItem(QListWidgetItem(f"  {i+1}.  reference_{i+1:03d}.jpg    5:00"))
    pl.addWidget(lw, 1)

    bot = QHBoxLayout()
    bot.setSpacing(4)
    for icon_name in ["ph.list-bullets-bold", "ph.squares-four-bold"]:
        b = QPushButton()
        b.setIcon(qta.icon(icon_name, color=t["btn_text"]))
        b.setIconSize(QSize(12, 12))
        b.setFixedSize(20, 20)
        b.setStyleSheet(f"background-color: {t['btn']}; border: 1px solid {t['border']};")
        bot.addWidget(b)
    bot.addStretch()
    pl.addLayout(bot)
    return panel


# ============================================================
# STRIP QUICK — compact
# ============================================================
def _strip_quick_compact(t):
    w = QWidget()
    w.setFixedSize(460, 160)
    w.setStyleSheet(f"background-color: {t['bg']};")
    root = QVBoxLayout(w)
    root.setContentsMargins(12, 8, 12, 8)
    root.setSpacing(6)

    tag = QLabel("Strip — Quick mode (compact)")
    tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
    tag.setStyleSheet(f"color: {t['hint']}; font-size: 9px;")
    root.addWidget(tag)

    # Top: title + mode + count + expand + add
    top = QHBoxLayout()
    top.setSpacing(6)
    title = QLabel("REFBOT")
    title.setStyleSheet(f"color: {t['header']}; font-size: 11px; font-weight: 500; letter-spacing: 2px;")
    top.addWidget(title)
    top.addSpacing(4)
    top.addLayout(_mode_toggle(t, "quick"))
    top.addStretch()
    count = QLabel("12 images")
    count.setStyleSheet(f"color: {t['secondary']}; font-size: 10px;")
    top.addWidget(count)
    expand = QPushButton()
    expand.setIcon(qta.icon("ph.arrows-out-bold", color=t["btn_text"]))
    expand.setIconSize(QSize(12, 12))
    expand.setFixedSize(22, 20)
    expand.setStyleSheet(f"background-color: {t['btn']}; border: 1px solid {t['border']};")
    top.addWidget(expand)
    add = QPushButton()
    add.setIcon(qta.icon("ph.plus-bold", color=t["btn_text"]))
    add.setIconSize(QSize(12, 12))
    add.setFixedSize(22, 20)
    add.setStyleSheet(f"background-color: {t['btn']}; border: 1px solid {t['border']};")
    top.addWidget(add)
    root.addLayout(top)

    # Timer presets row
    mid = QHBoxLayout()
    mid.setSpacing(3)
    for pl in ["30s", "1m", "2m", "5m", "10m", "15m", "30m", "1h"]:
        pb = QPushButton(pl)
        if pl == "5m":
            pb.setStyleSheet(
                f"background-color: {t['active']}; color: {t['primary']}; "
                f"border: 1px solid {t['accent']}; font-size: 10px; padding: 4px 6px;")
        else:
            pb.setStyleSheet(
                f"background-color: {t['btn']}; color: {t['secondary']}; "
                f"border: 1px solid {t['border']}; font-size: 10px; padding: 4px 6px;")
        mid.addWidget(pb)
    mid.addStretch()
    root.addLayout(mid)

    # Bottom: toggles + total + start
    bot = QHBoxLayout()
    bot.setSpacing(6)
    bot.addWidget(_icon_toggle(t, "ph.dice-five-fill", "ph.dice-three-bold", False))
    bot.addWidget(_icon_toggle(t, "ph.push-pin-fill", "ph.push-pin-bold", False))
    bot.addStretch()
    dur = QLabel("Total: 1:00:00")
    dur.setStyleSheet(f"color: {t['secondary']}; font-size: 11px;")
    bot.addWidget(dur)
    bot.addWidget(_start_btn(t, 36))
    root.addLayout(bot)

    return w


# ============================================================
# STRIP SESSION — compact
# ============================================================
def _strip_session_compact(t):
    w = QWidget()
    w.setFixedSize(460, 200)
    w.setStyleSheet(f"background-color: {t['bg']};")
    root = QVBoxLayout(w)
    root.setContentsMargins(12, 8, 12, 8)
    root.setSpacing(6)

    tag = QLabel("Strip — Session mode (compact)")
    tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
    tag.setStyleSheet(f"color: {t['hint']}; font-size: 9px;")
    root.addWidget(tag)

    # Top: title + mode + session duration + expand + add
    top = QHBoxLayout()
    top.setSpacing(6)
    title = QLabel("REFBOT")
    title.setStyleSheet(f"color: {t['header']}; font-size: 11px; font-weight: 500; letter-spacing: 2px;")
    top.addWidget(title)
    top.addSpacing(4)
    top.addLayout(_mode_toggle(t, "session"))
    top.addStretch()
    count = QLabel("12 images")
    count.setStyleSheet(f"color: {t['secondary']}; font-size: 10px;")
    top.addWidget(count)
    expand = QPushButton()
    expand.setIcon(qta.icon("ph.arrows-out-bold", color=t["btn_text"]))
    expand.setIconSize(QSize(12, 12))
    expand.setFixedSize(22, 20)
    expand.setStyleSheet(f"background-color: {t['btn']}; border: 1px solid {t['border']};")
    top.addWidget(expand)
    add = QPushButton()
    add.setIcon(qta.icon("ph.plus-bold", color=t["btn_text"]))
    add.setIconSize(QSize(12, 12))
    add.setFixedSize(22, 20)
    add.setStyleSheet(f"background-color: {t['btn']}; border: 1px solid {t['border']};")
    top.addWidget(add)
    root.addLayout(top)

    # Session duration row: < 1:00:00 >
    dur_row = QHBoxLayout()
    dur_row.addStretch()
    left_arr = QPushButton()
    left_arr.setIcon(qta.icon("ph.caret-left-bold", color=t["secondary"]))
    left_arr.setIconSize(QSize(14, 14))
    left_arr.setFixedSize(22, 22)
    left_arr.setStyleSheet("background: transparent; border: none;")
    dur_row.addWidget(left_arr)
    ses_display = QLabel("1:00:00")
    ses_display.setStyleSheet(f"color: {t['primary']}; font-size: 20px; font-weight: 400;")
    dur_row.addWidget(ses_display)
    right_arr = QPushButton()
    right_arr.setIcon(qta.icon("ph.caret-right-bold", color=t["secondary"]))
    right_arr.setIconSize(QSize(14, 14))
    right_arr.setFixedSize(22, 22)
    right_arr.setStyleSheet("background: transparent; border: none;")
    dur_row.addWidget(right_arr)
    dur_row.addStretch()
    root.addLayout(dur_row)

    # Tier toggles
    tier_row = QHBoxLayout()
    tier_row.setSpacing(3)
    tier_row.addStretch()
    for lb in ["30s", "1m", "3m", "5m", "10m", "15m", "30m", "1h"]:
        pb = QPushButton(lb)
        if lb in ("1m", "5m", "10m"):
            pb.setStyleSheet(
                f"background-color: {t['active']}; color: {t['primary']}; "
                f"border: 1px solid {t['accent']}; font-size: 9px; padding: 3px 5px;")
        else:
            pb.setStyleSheet(
                f"background-color: {t['btn']}; color: {t['secondary']}; "
                f"border: 1px solid {t['border']}; font-size: 9px; padding: 3px 5px;")
        tier_row.addWidget(pb)
    tier_row.addStretch()
    root.addLayout(tier_row)

    # Bottom: toggles + groups + auto + start
    bot = QHBoxLayout()
    bot.setSpacing(6)
    bot.addWidget(_icon_toggle(t, "ph.dice-five-fill", "ph.dice-three-bold", True))
    bot.addWidget(_icon_toggle(t, "ph.push-pin-fill", "ph.push-pin-bold", False))
    bot.addSpacing(8)
    groups = QLabel("4x1m  4x5m  4x10m")
    groups.setStyleSheet(f"color: {t['secondary']}; font-size: 10px;")
    bot.addWidget(groups)
    bot.addStretch()
    auto_btn = QPushButton("Auto")
    auto_btn.setStyleSheet(
        f"background-color: {t['btn']}; color: {t['secondary']}; "
        f"border: 1px solid {t['border']}; font-size: 9px; padding: 3px 8px;")
    bot.addWidget(auto_btn)
    reset = QPushButton()
    reset.setIcon(qta.icon("ph.x-bold", color=t["secondary"]))
    reset.setIconSize(QSize(10, 10))
    reset.setFixedSize(20, 20)
    reset.setStyleSheet(f"background-color: {t['btn']}; border: 1px solid {t['border']};")
    bot.addWidget(reset)
    bot.addWidget(_start_btn(t, 36))
    root.addLayout(bot)

    return w


# ============================================================
# STRIP QUICK — wide
# ============================================================
def _strip_quick_wide(t):
    w = QWidget()
    w.setFixedSize(460, 400)
    w.setStyleSheet(f"background-color: {t['bg']};")
    root = QVBoxLayout(w)
    root.setContentsMargins(12, 8, 12, 8)
    root.setSpacing(6)

    tag = QLabel("Strip — Quick mode (wide, editor open)")
    tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
    tag.setStyleSheet(f"color: {t['hint']}; font-size: 9px;")
    root.addWidget(tag)

    top = QHBoxLayout()
    top.setSpacing(6)
    title = QLabel("REFBOT")
    title.setStyleSheet(f"color: {t['header']}; font-size: 11px; font-weight: 500; letter-spacing: 2px;")
    top.addWidget(title)
    top.addSpacing(4)
    top.addLayout(_mode_toggle(t, "quick"))
    top.addStretch()
    count = QLabel("12 images")
    count.setStyleSheet(f"color: {t['secondary']}; font-size: 10px;")
    top.addWidget(count)
    collapse = QPushButton()
    collapse.setIcon(qta.icon("ph.arrows-in-bold", color=t["btn_text"]))
    collapse.setIconSize(QSize(12, 12))
    collapse.setFixedSize(22, 20)
    collapse.setStyleSheet(f"background-color: {t['btn']}; border: 1px solid {t['border']};")
    top.addWidget(collapse)
    add = QPushButton()
    add.setIcon(qta.icon("ph.plus-bold", color=t["btn_text"]))
    add.setIconSize(QSize(12, 12))
    add.setFixedSize(22, 20)
    add.setStyleSheet(f"background-color: {t['btn']}; border: 1px solid {t['border']};")
    top.addWidget(add)
    root.addLayout(top)

    mid = QHBoxLayout()
    mid.setSpacing(3)
    for pl in ["30s", "1m", "2m", "5m", "10m", "15m", "30m", "1h"]:
        pb = QPushButton(pl)
        if pl == "5m":
            pb.setStyleSheet(
                f"background-color: {t['active']}; color: {t['primary']}; "
                f"border: 1px solid {t['accent']}; font-size: 10px; padding: 4px 6px;")
        else:
            pb.setStyleSheet(
                f"background-color: {t['btn']}; color: {t['secondary']}; "
                f"border: 1px solid {t['border']}; font-size: 10px; padding: 4px 6px;")
        mid.addWidget(pb)
    mid.addStretch()
    root.addLayout(mid)

    bot = QHBoxLayout()
    bot.setSpacing(6)
    bot.addWidget(_icon_toggle(t, "ph.dice-five-fill", "ph.dice-three-bold", False))
    bot.addWidget(_icon_toggle(t, "ph.push-pin-fill", "ph.push-pin-bold", False))
    bot.addStretch()
    dur = QLabel("Total: 1:00:00")
    dur.setStyleSheet(f"color: {t['secondary']}; font-size: 11px;")
    bot.addWidget(dur)
    bot.addWidget(_start_btn(t, 36))
    root.addLayout(bot)

    root.addWidget(_sep_h(t))
    root.addWidget(_editor_panel(t), 1)

    return w


def main():
    app = QApplication(sys.argv)
    t = DARK

    widgets = [
        _strip_quick_compact(t),
        _strip_session_compact(t),
        _strip_quick_wide(t),
    ]
    for w in widgets:
        w.show()

    def capture():
        pixmaps = [w.grab() for w in widgets]
        gap = 10

        # Row 1: quick compact + session compact
        r1_w = pixmaps[0].width() + pixmaps[1].width() + gap * 3
        r1_h = max(pixmaps[0].height(), pixmaps[1].height())

        # Row 2: quick wide (full width)
        r2_w = pixmaps[2].width() + gap * 2
        r2_h = pixmaps[2].height()

        total_w = max(r1_w, r2_w)
        total_h = r1_h + r2_h + gap * 3

        result = QPixmap(total_w, total_h)
        result.fill(QColor("#111"))
        p = QPainter(result)

        x = gap
        p.drawPixmap(x, gap, pixmaps[0])
        x += pixmaps[0].width() + gap
        p.drawPixmap(x, gap, pixmaps[1])

        p.drawPixmap(gap, r1_h + gap * 2, pixmaps[2])

        p.end()
        result.save("mockup_strip_modes.png")
        print("Saved mockup_strip_modes.png")
        app.quit()

    QTimer.singleShot(300, capture)
    app.exec()

if __name__ == "__main__":
    main()
