"""Toggle mockups: compact ↔ wide for Timer Focus and Strip layouts."""
import sys
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                              QLabel, QPushButton, QCheckBox, QFrame, QListWidget,
                              QListWidgetItem)
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


def _start_btn(t, size=48):
    btn = QPushButton()
    icon_sz = int(size * ICON_RATIO)
    radius = int(size * RADIUS_RATIO)
    btn.setIcon(qta.icon(ICON, color=t["start_text"]))
    btn.setIconSize(QSize(icon_sz, icon_sz))
    btn.setFixedSize(size, size)
    btn.setStyleSheet(
        f"background-color: {t['accent']}; border: none; border-radius: {radius}px;")
    return btn


def _sep_h(t):
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet(f"color: {t['border']};")
    line.setFixedHeight(1)
    return line


def _sep_v(t):
    line = QFrame()
    line.setFrameShape(QFrame.Shape.VLine)
    line.setStyleSheet(f"color: {t['border']};")
    line.setFixedWidth(1)
    return line


def _mode_toggle(t):
    mr = QHBoxLayout()
    mr.setSpacing(0)
    for i, lb in enumerate(["Quick", "Session"]):
        b = QPushButton(lb)
        s = t['active'] if i == 0 else t['bg']
        c = t['primary'] if i == 0 else t['secondary']
        b.setStyleSheet(
            f"background-color: {s}; color: {c}; "
            f"border: 1px solid {t['border']}; font-size: 11px; font-weight: 500; padding: 5px;")
        mr.addWidget(b)
    return mr


def _presets_single_row(t):
    pr = QHBoxLayout()
    pr.setSpacing(3)
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
    return pr


def _presets_two_rows(t):
    outer = QVBoxLayout()
    outer.setSpacing(3)
    for row_labels in [["30s", "1m", "5m", "10m"], ["2m", "15m", "30m", "1h"]]:
        pr = QHBoxLayout()
        pr.setSpacing(3)
        pr.addStretch()
        for pl in row_labels:
            pb = QPushButton(pl)
            if pl == "5m":
                pb.setStyleSheet(
                    f"background-color: {t['active']}; color: {t['primary']}; "
                    f"border: 1px solid {t['accent']}; font-size: 11px; font-weight: 500; padding: 5px 10px;")
            else:
                pb.setStyleSheet(
                    f"background-color: {t['btn']}; color: {t['secondary']}; "
                    f"border: 1px solid {t['border']}; font-size: 11px; font-weight: 500; padding: 5px 10px;")
            pr.addWidget(pb)
        pr.addStretch()
        outer.addLayout(pr)
    return outer


def _editor_panel(t, height=None):
    """Simulated image editor panel."""
    panel = QWidget()
    if height:
        panel.setFixedHeight(height)
    pl = QVBoxLayout(panel)
    pl.setContentsMargins(8, 6, 8, 6)
    pl.setSpacing(4)

    # Toolbar
    tb = QHBoxLayout()
    tb.setSpacing(4)
    for icon_name, tip in [("ph.file-plus-bold", "Add files"), ("ph.folder-plus-bold", "Add folder"),
                            ("ph.link-bold", "URL")]:
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

    # File list
    lw = QListWidget()
    lw.setStyleSheet(
        f"QListWidget {{ background-color: {t['bg2']}; border: none; "
        f"font-size: 10px; color: {t['primary']}; }}"
        f"QListWidget::item {{ padding: 2px; }}")
    for i in range(8):
        item = QListWidgetItem(f"  {i+1}.  reference_{i+1:03d}.jpg    5:00")
        lw.addItem(item)
    pl.addWidget(lw, 1)

    # Bottom
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


def _arrow_label(t, text):
    lbl = QLabel(text)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setStyleSheet(f"color: {t['accent']}; font-size: 20px;")
    lbl.setFixedWidth(40)
    return lbl


# ============================================================
# TIMER FOCUS
# ============================================================

def _timer_compact(t):
    w = QWidget()
    w.setFixedSize(300, 480)
    w.setStyleSheet(f"background-color: {t['bg']};")
    root = QVBoxLayout(w)
    root.setContentsMargins(14, 10, 14, 10)
    root.setSpacing(6)

    tag = QLabel("Timer Focus — compact")
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

    root.addSpacing(6)
    root.addLayout(_mode_toggle(t))
    root.addSpacing(4)

    # Big timer
    td = QLabel("5:00")
    td.setAlignment(Qt.AlignmentFlag.AlignCenter)
    td.setStyleSheet(f"color: {t['primary']}; font-size: 44px; font-weight: 300;")
    root.addWidget(td)
    sub = QLabel("per image")
    sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
    sub.setStyleSheet(f"color: {t['hint']}; font-size: 10px;")
    root.addWidget(sub)

    root.addSpacing(4)
    root.addLayout(_presets_single_row(t))
    root.addSpacing(6)
    root.addWidget(_sep_h(t))
    root.addSpacing(4)

    # Images row
    img_row = QHBoxLayout()
    img_count = QLabel("12 images")
    img_count.setStyleSheet(f"color: {t['secondary']}; font-size: 11px;")
    img_row.addWidget(img_count)
    img_row.addStretch()
    # Toggle to wide
    expand = QPushButton()
    expand.setIcon(qta.icon("ph.arrows-out-bold", color=t["btn_text"]))
    expand.setIconSize(QSize(12, 12))
    expand.setFixedSize(22, 22)
    expand.setToolTip("Expand editor")
    expand.setStyleSheet(f"background-color: {t['btn']}; border: 1px solid {t['border']};")
    img_row.addWidget(expand)
    add_btn = QPushButton()
    add_btn.setIcon(qta.icon("ph.plus-bold", color=t["btn_text"]))
    add_btn.setIconSize(QSize(12, 12))
    add_btn.setFixedSize(22, 22)
    add_btn.setStyleSheet(f"background-color: {t['btn']}; border: 1px solid {t['border']};")
    img_row.addWidget(add_btn)
    root.addLayout(img_row)

    # Thumb strip
    tr = QHBoxLayout()
    tr.setSpacing(2)
    for _ in range(7):
        tb = QLabel()
        tb.setFixedSize(30, 30)
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

    bl = QHBoxLayout()
    bl.addStretch()
    bl.addWidget(_start_btn(t, 48))
    bl.addStretch()
    root.addLayout(bl)
    return w


def _timer_wide(t):
    w = QWidget()
    w.setFixedSize(600, 480)
    w.setStyleSheet(f"background-color: {t['bg']};")
    root = QHBoxLayout(w)
    root.setContentsMargins(12, 10, 12, 10)
    root.setSpacing(0)

    # Left — timer controls (same as compact)
    left = QVBoxLayout()
    left.setSpacing(6)

    tag = QLabel("Timer Focus — wide (editor open)")
    tag.setStyleSheet(f"color: {t['hint']}; font-size: 9px;")
    left.addWidget(tag)

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
    left.addLayout(h)

    left.addSpacing(4)
    left.addLayout(_mode_toggle(t))
    left.addSpacing(4)

    td = QLabel("5:00")
    td.setAlignment(Qt.AlignmentFlag.AlignCenter)
    td.setStyleSheet(f"color: {t['primary']}; font-size: 44px; font-weight: 300;")
    left.addWidget(td)
    sub = QLabel("per image")
    sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
    sub.setStyleSheet(f"color: {t['hint']}; font-size: 10px;")
    left.addWidget(sub)

    left.addSpacing(4)
    left.addLayout(_presets_single_row(t))

    left.addSpacing(8)

    opt = QHBoxLayout()
    for text in ["Random", "On top"]:
        cb = QCheckBox(text)
        cb.setStyleSheet(f"color: {t['secondary']}; font-size: 10px;")
        opt.addWidget(cb)
    opt.addStretch()
    total = QLabel("Total: 1:00:00")
    total.setStyleSheet(f"color: {t['secondary']}; font-size: 11px;")
    opt.addWidget(total)
    left.addLayout(opt)

    left.addStretch()

    bl = QHBoxLayout()
    bl.addStretch()
    bl.addWidget(_start_btn(t, 48))
    bl.addStretch()
    left.addLayout(bl)

    left_w = QWidget()
    left_w.setFixedWidth(280)
    left_w.setLayout(left)
    root.addWidget(left_w)

    root.addWidget(_sep_v(t))

    # Right — editor panel
    root.addWidget(_editor_panel(t), 1)

    return w


# ============================================================
# STRIP
# ============================================================

def _strip_compact(t):
    w = QWidget()
    w.setFixedSize(460, 180)
    w.setStyleSheet(f"background-color: {t['bg']};")
    root = QVBoxLayout(w)
    root.setContentsMargins(12, 8, 12, 8)
    root.setSpacing(6)

    tag = QLabel("Strip — compact")
    tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
    tag.setStyleSheet(f"color: {t['hint']}; font-size: 9px;")
    root.addWidget(tag)

    # Top: title + mode + count + expand + add
    top = QHBoxLayout()
    top.setSpacing(6)
    title = QLabel("REFBOT")
    title.setStyleSheet(f"color: {t['header']}; font-size: 11px; font-weight: 500; letter-spacing: 2px;")
    top.addWidget(title)
    top.addSpacing(8)

    for i, lb in enumerate(["Quick", "Session"]):
        b = QPushButton(lb)
        s = t['active'] if i == 0 else t['bg']
        c = t['primary'] if i == 0 else t['secondary']
        b.setStyleSheet(
            f"background-color: {s}; color: {c}; "
            f"border: 1px solid {t['border']}; font-size: 9px; padding: 3px 6px;")
        top.addWidget(b)

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

    # Timer presets + start
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
    mid.addWidget(_start_btn(t, 36))
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


def _strip_wide(t):
    w = QWidget()
    w.setFixedSize(460, 420)
    w.setStyleSheet(f"background-color: {t['bg']};")
    root = QVBoxLayout(w)
    root.setContentsMargins(12, 8, 12, 8)
    root.setSpacing(6)

    tag = QLabel("Strip — wide (editor open below)")
    tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
    tag.setStyleSheet(f"color: {t['hint']}; font-size: 9px;")
    root.addWidget(tag)

    # Same top bar
    top = QHBoxLayout()
    top.setSpacing(6)
    title = QLabel("REFBOT")
    title.setStyleSheet(f"color: {t['header']}; font-size: 11px; font-weight: 500; letter-spacing: 2px;")
    top.addWidget(title)
    top.addSpacing(8)

    for i, lb in enumerate(["Quick", "Session"]):
        b = QPushButton(lb)
        s = t['active'] if i == 0 else t['bg']
        c = t['primary'] if i == 0 else t['secondary']
        b.setStyleSheet(
            f"background-color: {s}; color: {c}; "
            f"border: 1px solid {t['border']}; font-size: 9px; padding: 3px 6px;")
        top.addWidget(b)

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

    # Timer + start
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
    mid.addWidget(_start_btn(t, 36))
    root.addLayout(mid)

    # Options
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

    root.addWidget(_sep_h(t))

    # Editor panel below
    root.addWidget(_editor_panel(t), 1)

    return w


def main():
    app = QApplication(sys.argv)
    t = DARK

    widgets = [
        _timer_compact(t),
        _timer_wide(t),
        _strip_compact(t),
        _strip_wide(t),
    ]

    for w in widgets:
        w.show()

    def capture():
        pixmaps = [w.grab() for w in widgets]

        # Row 1: timer compact + arrow + timer wide
        # Row 2: strip compact + arrow + strip wide
        gap = 10
        arrow_w = 40
        r1_w = pixmaps[0].width() + arrow_w + pixmaps[1].width() + gap * 4
        r1_h = max(pixmaps[0].height(), pixmaps[1].height())
        r2_w = pixmaps[2].width() + arrow_w + pixmaps[3].width() + gap * 4
        r2_h = max(pixmaps[2].height(), pixmaps[3].height())

        total_w = max(r1_w, r2_w) + gap * 2
        total_h = r1_h + r2_h + gap * 3

        result = QPixmap(total_w, total_h)
        result.fill(QColor("#111"))
        p = QPainter(result)

        # Row 1
        y = gap
        x = gap
        p.drawPixmap(x, y, pixmaps[0])
        x += pixmaps[0].width() + gap
        # Arrow
        p.setPen(QColor(DARK["accent"]))
        from PyQt6.QtGui import QFont
        f = QFont()
        f.setPixelSize(24)
        p.setFont(f)
        p.drawText(x, y + r1_h // 2, "→")
        x += arrow_w + gap
        p.drawPixmap(x, y, pixmaps[1])

        # Row 2
        y = r1_h + gap * 2
        x = gap
        p.drawPixmap(x, y, pixmaps[2])
        x += pixmaps[2].width() + gap
        p.drawText(x, y + r2_h // 2, "→")
        x += arrow_w + gap
        p.drawPixmap(x, y, pixmaps[3])

        p.end()
        result.save("mockup_toggle.png")
        print("Saved mockup_toggle.png")
        app.quit()

    QTimer.singleShot(300, capture)
    app.exec()

if __name__ == "__main__":
    main()
