"""Layout mockups with fa6s.pencil square start button."""
import sys
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                              QLabel, QPushButton, QCheckBox, QFrame)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QPixmap, QPainter, QColor
import qtawesome as qta

ICON = "fa6s.pencil"
ICON_RATIO = 0.75
RADIUS_RATIO = 0.12
BTN_SZ = 48

DARK = {
    "bg": "#191919", "bg2": "#171717", "btn": "#222222",
    "active": "#333b3a", "border": "#303030", "accent": "#4a7d74",
    "primary": "#ddd", "secondary": "#606060", "hint": "#454545",
    "header": "#84a39e", "btn_text": "#84a39e", "start_text": "#252525",
}

LIGHT = {
    "bg": "#d4d4d4", "bg2": "#dddddd", "btn": "#c6c6c6",
    "active": "#bfd1ce", "border": "#a5a5a5", "accent": "#4a7d74",
    "primary": "#222", "secondary": "#5a5a5a", "hint": "#858585",
    "header": "#3e6a62", "btn_text": "#3e6a62", "start_text": "#c4c4c4",
}


def _start_btn(t, size=BTN_SZ):
    btn = QPushButton()
    icon_sz = int(size * ICON_RATIO)
    radius = int(size * RADIUS_RATIO)
    btn.setIcon(qta.icon(ICON, color=t["start_text"]))
    btn.setIconSize(QSize(icon_sz, icon_sz))
    btn.setFixedSize(size, size)
    btn.setStyleSheet(
        f"background-color: {t['accent']}; border: none; border-radius: {radius}px;")
    return btn


def _sep(t):
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet(f"color: {t['border']};")
    line.setFixedHeight(1)
    return line


def _build_vertical(t, label):
    """Classic vertical — current layout shape but with square start button."""
    w = QWidget()
    w.setFixedSize(340, 480)
    w.setStyleSheet(f"background-color: {t['bg']};")
    root = QVBoxLayout(w)
    root.setContentsMargins(16, 12, 16, 12)
    root.setSpacing(10)

    tag = QLabel(f"A) Vertical — {label}")
    tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
    tag.setStyleSheet(f"color: {t['hint']}; font-size: 9px;")
    root.addWidget(tag)

    # Header
    h = QHBoxLayout()
    info = QPushButton()
    info.setIcon(qta.icon("ph.info-bold", color=t["hint"]))
    info.setIconSize(QSize(16, 16))
    info.setFixedSize(22, 22)
    info.setStyleSheet("background: transparent; border: none;")
    h.addWidget(info)
    h.addStretch()
    title = QLabel("REFBOT")
    title.setStyleSheet(f"color: {t['header']}; font-size: 13px; font-weight: 500; letter-spacing: 3px;")
    h.addWidget(title)
    h.addStretch()
    moon = QPushButton()
    moon.setIcon(qta.icon("ph.moon-bold", color=t["hint"]))
    moon.setIconSize(QSize(16, 16))
    moon.setFixedSize(22, 22)
    moon.setStyleSheet("background: transparent; border: none;")
    h.addWidget(moon)
    root.addLayout(h)

    # Drop zone
    drop = QLabel("Drop images here\nor click to browse")
    drop.setAlignment(Qt.AlignmentFlag.AlignCenter)
    drop.setFixedHeight(64)
    drop.setStyleSheet(
        f"background-color: {t['bg2']}; border: 1px dashed {t['accent']}; "
        f"color: {t['secondary']}; font-size: 12px;")
    root.addWidget(drop)

    # Mode toggle
    mr = QHBoxLayout()
    mr.setSpacing(0)
    for i, lb in enumerate(["Quick", "Session"]):
        b = QPushButton(lb)
        s = t['active'] if i == 0 else t['bg']
        c = t['primary'] if i == 0 else t['secondary']
        b.setStyleSheet(
            f"background-color: {s}; color: {c}; "
            f"border: 1px solid {t['border']}; font-size: 12px; font-weight: 500; padding: 6px;")
        mr.addWidget(b)
    root.addLayout(mr)

    # Presets
    for row_labels in [["30s", "1m", "5m", "10m"], ["2m", "15m", "30m", "1h"]]:
        pr = QHBoxLayout()
        pr.setSpacing(4)
        pr.addStretch()
        for pl in row_labels:
            pb = QPushButton(pl)
            if pl == "5m":
                pb.setStyleSheet(
                    f"background-color: {t['active']}; color: {t['primary']}; "
                    f"border: 1px solid {t['accent']}; font-size: 12px; font-weight: 500; padding: 6px 14px;")
            else:
                pb.setStyleSheet(
                    f"background-color: {t['btn']}; color: {t['secondary']}; "
                    f"border: 1px solid {t['border']}; font-size: 12px; font-weight: 500; padding: 6px 14px;")
            pr.addWidget(pb)
        pr.addStretch()
        root.addLayout(pr)

    # Options + summary
    for text in ["Random order", "Always on top"]:
        cb = QCheckBox(text)
        cb.setStyleSheet(f"color: {t['secondary']}; font-size: 10px;")
        root.addWidget(cb)

    summary = QLabel("12 images / 1:00:00")
    summary.setAlignment(Qt.AlignmentFlag.AlignCenter)
    summary.setStyleSheet(f"color: {t['secondary']}; font-size: 12px;")
    root.addWidget(summary)

    root.addStretch()

    # Start button — centered square
    bl = QHBoxLayout()
    bl.addStretch()
    bl.addWidget(_start_btn(t))
    bl.addStretch()
    root.addLayout(bl)

    return w


def _build_wide(t, label):
    """Wide horizontal — images left, controls right."""
    w = QWidget()
    w.setFixedSize(520, 340)
    w.setStyleSheet(f"background-color: {t['bg']};")
    root = QHBoxLayout(w)
    root.setContentsMargins(12, 10, 12, 10)
    root.setSpacing(12)

    # Left — images
    left = QVBoxLayout()
    left.setSpacing(6)

    tag = QLabel(f"B) Wide — {label}")
    tag.setStyleSheet(f"color: {t['hint']}; font-size: 9px;")
    left.addWidget(tag)

    title = QLabel("REFBOT")
    title.setStyleSheet(f"color: {t['header']}; font-size: 13px; font-weight: 500; letter-spacing: 3px;")
    left.addWidget(title)

    drop = QLabel("Drop images here\nor click to browse")
    drop.setAlignment(Qt.AlignmentFlag.AlignCenter)
    drop.setFixedHeight(56)
    drop.setStyleSheet(
        f"background-color: {t['bg2']}; border: 1px dashed {t['accent']}; "
        f"color: {t['secondary']}; font-size: 11px;")
    left.addWidget(drop)

    for row in range(3):
        tr = QHBoxLayout()
        tr.setSpacing(2)
        for _ in range(5):
            tb = QLabel()
            tb.setFixedSize(36, 36)
            tb.setStyleSheet(f"background-color: {t['bg2']};")
            tr.addWidget(tb)
        tr.addStretch()
        left.addLayout(tr)

    left.addStretch()
    summary = QLabel("12 images / 1:00:00")
    summary.setStyleSheet(f"color: {t['secondary']}; font-size: 11px;")
    left.addWidget(summary)

    root.addLayout(left, 1)

    div = QFrame()
    div.setFrameShape(QFrame.Shape.VLine)
    div.setStyleSheet(f"color: {t['border']};")
    div.setFixedWidth(1)
    root.addWidget(div)

    # Right — controls
    right = QVBoxLayout()
    right.setSpacing(8)

    mr = QHBoxLayout()
    mr.setSpacing(0)
    for i, lb in enumerate(["Quick", "Session"]):
        b = QPushButton(lb)
        s = t['active'] if i == 0 else t['bg']
        c = t['primary'] if i == 0 else t['secondary']
        b.setStyleSheet(
            f"background-color: {s}; color: {c}; "
            f"border: 1px solid {t['border']}; font-size: 11px; padding: 5px;")
        mr.addWidget(b)
    right.addLayout(mr)

    for row_labels in [["30s", "1m", "5m", "10m"], ["2m", "15m", "30m", "1h"]]:
        pr = QHBoxLayout()
        pr.setSpacing(3)
        for pl in row_labels:
            pb = QPushButton(pl)
            if pl == "5m":
                pb.setStyleSheet(
                    f"background-color: {t['active']}; color: {t['primary']}; "
                    f"border: 1px solid {t['accent']}; font-size: 11px; padding: 5px 8px;")
            else:
                pb.setStyleSheet(
                    f"background-color: {t['btn']}; color: {t['secondary']}; "
                    f"border: 1px solid {t['border']}; font-size: 11px; padding: 5px 8px;")
            pr.addWidget(pb)
        right.addLayout(pr)

    right.addWidget(_sep(t))

    for text in ["Random order", "Always on top"]:
        cb = QCheckBox(text)
        cb.setStyleSheet(f"color: {t['secondary']}; font-size: 10px;")
        right.addWidget(cb)

    right.addStretch()

    bl = QHBoxLayout()
    bl.addStretch()
    bl.addWidget(_start_btn(t))
    bl.addStretch()
    right.addLayout(bl)

    root.addLayout(right, 1)
    return w


def _build_strip(t, label):
    """Minimal strip — everything compact."""
    w = QWidget()
    w.setFixedSize(500, 180)
    w.setStyleSheet(f"background-color: {t['bg']};")
    root = QVBoxLayout(w)
    root.setContentsMargins(14, 10, 14, 10)
    root.setSpacing(8)

    tag = QLabel(f"C) Strip — {label}")
    tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
    tag.setStyleSheet(f"color: {t['hint']}; font-size: 9px;")
    root.addWidget(tag)

    # Top: title + count + add
    top = QHBoxLayout()
    title = QLabel("REFBOT")
    title.setStyleSheet(f"color: {t['header']}; font-size: 11px; font-weight: 500; letter-spacing: 2px;")
    top.addWidget(title)
    top.addStretch()
    count = QLabel("12 images")
    count.setStyleSheet(f"color: {t['secondary']}; font-size: 11px;")
    top.addWidget(count)
    add = QPushButton()
    add.setIcon(qta.icon("ph.plus-bold", color=t["btn_text"]))
    add.setIconSize(QSize(14, 14))
    add.setFixedSize(24, 22)
    add.setStyleSheet(f"background-color: {t['btn']}; border: 1px solid {t['border']};")
    top.addWidget(add)
    root.addLayout(top)

    # Timer + options + start in one row
    mid = QHBoxLayout()
    mid.setSpacing(4)
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
    mid.addWidget(_start_btn(t, 40))
    root.addLayout(mid)

    # Bottom: options + duration
    bot = QHBoxLayout()
    for text in ["Random", "On top"]:
        cb = QCheckBox(text)
        cb.setStyleSheet(f"color: {t['secondary']}; font-size: 10px;")
        bot.addWidget(cb)
    bot.addStretch()
    dur = QLabel("Total: 1:00:00")
    dur.setStyleSheet(f"color: {t['secondary']}; font-size: 11px;")
    bot.addWidget(dur)
    root.addLayout(bot)

    return w


def _build_timer_focus(t, label):
    """Timer hero — big number, square start button below."""
    w = QWidget()
    w.setFixedSize(340, 480)
    w.setStyleSheet(f"background-color: {t['bg']};")
    root = QVBoxLayout(w)
    root.setContentsMargins(16, 14, 16, 14)
    root.setSpacing(6)

    tag = QLabel(f"D) Timer Focus — {label}")
    tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
    tag.setStyleSheet(f"color: {t['hint']}; font-size: 9px;")
    root.addWidget(tag)

    # Header
    h = QHBoxLayout()
    info = QPushButton()
    info.setIcon(qta.icon("ph.info-bold", color=t["hint"]))
    info.setIconSize(QSize(14, 14))
    info.setFixedSize(20, 20)
    info.setStyleSheet("background: transparent; border: none;")
    h.addWidget(info)
    h.addStretch()
    title = QLabel("REFBOT")
    title.setStyleSheet(f"color: {t['header']}; font-size: 12px; font-weight: 500; letter-spacing: 3px;")
    h.addWidget(title)
    h.addStretch()
    moon = QPushButton()
    moon.setIcon(qta.icon("ph.moon-bold", color=t["hint"]))
    moon.setIconSize(QSize(14, 14))
    moon.setFixedSize(20, 20)
    moon.setStyleSheet("background: transparent; border: none;")
    h.addWidget(moon)
    root.addLayout(h)

    root.addSpacing(10)

    # Big timer
    time_display = QLabel("5:00")
    time_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
    time_display.setStyleSheet(f"color: {t['primary']}; font-size: 48px; font-weight: 300;")
    root.addWidget(time_display)

    sub = QLabel("per image")
    sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
    sub.setStyleSheet(f"color: {t['hint']}; font-size: 10px;")
    root.addWidget(sub)

    root.addSpacing(6)

    pr = QHBoxLayout()
    pr.setSpacing(4)
    pr.addStretch()
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
        pr.addWidget(pb)
    pr.addStretch()
    root.addLayout(pr)

    root.addSpacing(8)
    root.addWidget(_sep(t))
    root.addSpacing(4)

    # Images row
    img_row = QHBoxLayout()
    img_count = QLabel("12 images")
    img_count.setStyleSheet(f"color: {t['secondary']}; font-size: 11px;")
    img_row.addWidget(img_count)
    img_row.addStretch()
    add_btn = QPushButton()
    add_btn.setIcon(qta.icon("ph.plus-bold", color=t["btn_text"]))
    add_btn.setIconSize(QSize(12, 12))
    add_btn.setFixedSize(22, 22)
    add_btn.setStyleSheet(f"background-color: {t['btn']}; border: 1px solid {t['border']};")
    img_row.addWidget(add_btn)
    root.addLayout(img_row)

    tr = QHBoxLayout()
    tr.setSpacing(2)
    for _ in range(8):
        tb = QLabel()
        tb.setFixedSize(32, 32)
        tb.setStyleSheet(f"background-color: {t['bg2']};")
        tr.addWidget(tb)
    tr.addStretch()
    root.addLayout(tr)

    # Options
    opt = QHBoxLayout()
    for text in ["Random", "On top"]:
        cb = QCheckBox(text)
        cb.setStyleSheet(f"color: {t['secondary']}; font-size: 10px;")
        opt.addWidget(cb)
    opt.addStretch()
    total = QLabel("Total: 1:00:00")
    total.setStyleSheet(f"color: {t['secondary']}; font-size: 11px;")
    opt.addWidget(total)
    root.addLayout(opt)

    root.addStretch()

    # Start — centered
    bl = QHBoxLayout()
    bl.addStretch()
    bl.addWidget(_start_btn(t, 56))
    bl.addStretch()
    root.addLayout(bl)

    return w


def main():
    app = QApplication(sys.argv)

    builders = [
        ("vertical", _build_vertical),
        ("wide", _build_wide),
        ("strip", _build_strip),
        ("timer", _build_timer_focus),
    ]

    # Dark
    dark_widgets = [(n, fn(DARK, "dark")) for n, fn in builders]
    # Light
    light_widgets = [(n, fn(LIGHT, "light")) for n, fn in builders]

    all_w = dark_widgets + light_widgets
    for _, w in all_w:
        w.show()

    def capture():
        dark_pixmaps = [w.grab() for _, w in dark_widgets]
        light_pixmaps = [w.grab() for _, w in light_widgets]

        # Layout: two rows (dark on top, light below), 4 columns
        gap = 10
        col_widths = [max(dp.width(), lp.width()) for dp, lp in zip(dark_pixmaps, light_pixmaps)]
        total_w = sum(col_widths) + gap * (len(col_widths) + 1)
        dark_h = max(p.height() for p in dark_pixmaps)
        light_h = max(p.height() for p in light_pixmaps)
        total_h = dark_h + light_h + gap * 3

        result = QPixmap(total_w, total_h)
        result.fill(QColor("#111"))
        p = QPainter(result)

        x = gap
        for i, pix in enumerate(dark_pixmaps):
            p.drawPixmap(x, gap, pix)
            x += col_widths[i] + gap

        x = gap
        for i, pix in enumerate(light_pixmaps):
            p.drawPixmap(x, dark_h + gap * 2, pix)
            x += col_widths[i] + gap

        p.end()
        result.save("mockup_layouts.png")
        print("Saved mockup_layouts.png")
        app.quit()

    QTimer.singleShot(300, capture)
    app.exec()

if __name__ == "__main__":
    main()
