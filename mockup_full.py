"""Full overview: dark/light, class/quick, list/grid — docked right."""
import sys
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                              QLabel, QPushButton, QFrame, QSlider, QScrollArea)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QPixmap, QPainter, QColor
import qtawesome as qta

ICON = "fa6s.pencil"
ICON_RATIO = 0.75
RADIUS_RATIO = 0.12
M = 14
M_BOT = 18
COMPACT_W = 250
COMPACT_H = 270
START_SZ = 42
EDITOR_W = 250
DUR_ROW_H = 40

DARK = {
    "bg": "#191919", "bg2": "#171717", "btn": "#222222",
    "active": "#333b3a", "border": "#303030", "accent": "#4a7d74",
    "primary": "#ddd", "secondary": "#606060", "hint": "#454545",
    "header": "#84a39e", "btn_text": "#84a39e", "start_text": "#252525",
    "warning": "#cc5555",
}

LIGHT = {
    "bg": "#d4d4d4", "bg2": "#dddddd", "btn": "#c6c6c6",
    "active": "#bfd1ce", "border": "#a5a5a5", "accent": "#4a7d74",
    "primary": "#222", "secondary": "#5a5a5a", "hint": "#858585",
    "header": "#3e6a62", "btn_text": "#3e6a62", "start_text": "#c4c4c4",
    "warning": "#cc4444",
}

BTN_ACTIVE = ("background-color: {active}; color: {primary}; "
              "border: 1px solid {accent}; font-size: 10px; padding: 4px 7px;")
BTN_INACTIVE = ("background-color: {btn}; color: {secondary}; "
                "border: 1px solid {border}; font-size: 10px; padding: 4px 7px;")


def _start_btn(t, size=START_SZ):
    btn = QPushButton()
    btn.setIcon(qta.icon(ICON, color=t["start_text"]))
    btn.setIconSize(QSize(int(size * ICON_RATIO), int(size * ICON_RATIO)))
    btn.setFixedSize(size, size)
    btn.setStyleSheet(
        f"background-color: {t['accent']}; border: none; "
        f"border-radius: {int(size * RADIUS_RATIO)}px;")
    return btn


def _icon_toggle(t, icon_on, icon_off, is_on, size=13):
    btn = QPushButton()
    color = t["accent"] if is_on else t["hint"]
    btn.setIcon(qta.icon(icon_on if is_on else icon_off, color=color))
    btn.setIconSize(QSize(size, size))
    btn.setFixedSize(size, size)
    btn.setStyleSheet("background: transparent; border: none; padding: 0px;")
    return btn


def _group_header(t, label, count, inactive=False):
    btn = QPushButton(f"  {label} — {count}")
    btn.setStyleSheet(
        f"background-color: {t['btn']}; color: {t['hint'] if inactive else t['secondary']}; "
        f"border: 1px solid {t['border']}; font-size: 9px; font-weight: 500; "
        f"padding: 2px 6px; text-align: left;")
    btn.setFixedHeight(18)
    return btn


def _file_row(t, idx, name, timer, pinned=False):
    w = QWidget()
    w.setFixedHeight(16)
    w.setStyleSheet("background: transparent;")
    row = QHBoxLayout(w)
    row.setContentsMargins(4, 0, 4, 0)
    row.setSpacing(3)
    num = QLabel(f"{idx}.")
    num.setFixedWidth(14)
    num.setStyleSheet(f"color: {t['hint']}; font-size: 9px; background: transparent;")
    row.addWidget(num)
    if pinned:
        pin = QLabel()
        pin.setPixmap(qta.icon("ph.push-pin-fill", color=t["accent"]).pixmap(QSize(8, 8)))
        pin.setFixedSize(8, 8)
        pin.setStyleSheet("background: transparent;")
        row.addWidget(pin)
    fname = QLabel(name)
    fname.setStyleSheet(
        f"color: {t['accent'] if pinned else t['primary']}; font-size: 9px; background: transparent;")
    row.addWidget(fname, 1)
    tl = QLabel(timer)
    tl.setStyleSheet(f"color: {t['secondary']}; font-size: 9px; background: transparent;")
    row.addWidget(tl)
    return w


def _file_row_reserve(t, idx, name):
    w = QWidget()
    w.setFixedHeight(16)
    w.setStyleSheet("background: transparent;")
    row = QHBoxLayout(w)
    row.setContentsMargins(4, 0, 4, 0)
    row.setSpacing(3)
    num = QLabel(f"{idx}.")
    num.setFixedWidth(14)
    num.setStyleSheet(f"color: {t['hint']}; font-size: 9px; background: transparent;")
    row.addWidget(num)
    fname = QLabel(name)
    fname.setStyleSheet(f"color: {t['hint']}; font-size: 9px; background: transparent;")
    row.addWidget(fname, 1)
    dash = QLabel("—")
    dash.setStyleSheet(f"color: {t['hint']}; font-size: 9px; background: transparent;")
    row.addWidget(dash)
    return w


def _tile(t, pinned=False, reserve=False):
    lbl = QLabel()
    lbl.setFixedSize(44, 44)
    if reserve:
        lbl.setStyleSheet(f"background-color: {t['btn']}; border: 1px dashed {t['hint']};")
    elif pinned:
        lbl.setStyleSheet(f"background-color: {t['bg2']}; border: 2px solid {t['accent']};")
    else:
        lbl.setStyleSheet(f"background-color: {t['bg2']}; border: 1px solid {t['border']};")
    return lbl


def _settings_panel(t, mode="class", dice_on=False, pin_on=False):
    panel = QWidget()
    panel.setFixedSize(COMPACT_W, COMPACT_H)
    panel.setStyleSheet(f"background-color: {t['bg']};")
    root = QVBoxLayout(panel)
    root.setContentsMargins(M, M, M, M_BOT)
    root.setSpacing(0)

    # Header
    header = QHBoxLayout()
    header.setContentsMargins(0, 0, 0, 0)
    header.setSpacing(0)
    lh = QHBoxLayout()
    lh.setSpacing(2)
    lh.setContentsMargins(0, 0, 0, 0)
    info = QPushButton()
    info.setIcon(qta.icon("ph.info-bold", color=t["hint"]))
    info.setIconSize(QSize(13, 13))
    info.setFixedSize(13, 13)
    info.setStyleSheet("background: transparent; border: none; padding: 0px;")
    lh.addWidget(info)
    lh.addWidget(_icon_toggle(t, "ph.push-pin-fill", "ph.push-pin-bold", pin_on))
    lh.addStretch()
    lww = QWidget()
    lww.setLayout(lh)
    lww.setStyleSheet("background: transparent;")

    rh = QHBoxLayout()
    rh.setSpacing(2)
    rh.setContentsMargins(0, 0, 0, 0)
    rh.addStretch()
    ad = QPushButton()
    ad.setFixedSize(11, 11)
    ad.setStyleSheet(
        f"background-color: {t['accent']}; border: 1px solid {t['border']}; "
        f"border-radius: 5px; padding: 0px;")
    rh.addWidget(ad)
    is_dark = t["bg"] == "#191919"
    moon_icon = "ph.moon-bold" if is_dark else "ph.sun-bold"
    moon = QPushButton()
    moon.setIcon(qta.icon(moon_icon, color=t["hint"]))
    moon.setIconSize(QSize(13, 13))
    moon.setFixedSize(13, 13)
    moon.setStyleSheet("background: transparent; border: none; padding: 0px;")
    rh.addWidget(moon)
    rww = QWidget()
    rww.setLayout(rh)
    rww.setStyleSheet("background: transparent;")

    title = QLabel("REFBOT")
    title.setAlignment(Qt.AlignmentFlag.AlignCenter)
    title.setStyleSheet(
        f"color: {t['header']}; font-size: 11px; font-weight: 500; letter-spacing: 3px;")
    header.addWidget(lww, 1)
    header.addWidget(title)
    header.addWidget(rww, 1)
    root.addLayout(header)
    root.addSpacing(6)

    # Mode toggle
    mr = QHBoxLayout()
    mr.setContentsMargins(0, 0, 0, 0)
    mr.setSpacing(0)
    for lb, key in [("Class", "class"), ("Quick", "quick")]:
        b = QPushButton(lb)
        active = key == mode
        b.setStyleSheet(
            f"background-color: {t['active'] if active else t['bg']}; "
            f"color: {t['primary'] if active else t['secondary']}; "
            f"border: 1px solid {t['border']}; font-size: 10px; font-weight: 500; padding: 3px 7px;")
        mr.addWidget(b)
    mr.addStretch()
    cnt = QLabel("11 img")
    cnt.setStyleSheet(f"color: {t['secondary']}; font-size: 10px;")
    mr.addWidget(cnt)
    mr.addSpacing(2)
    plus = QPushButton()
    plus.setIcon(qta.icon("ph.plus-bold", color=t["btn_text"]))
    plus.setIconSize(QSize(12, 12))
    plus.setFixedSize(20, 20)
    plus.setStyleSheet(f"background-color: {t['btn']}; border: 1px solid {t['border']};")
    mr.addWidget(plus)
    root.addLayout(mr)
    root.addSpacing(10)

    # Duration picker
    dr = QHBoxLayout()
    dr.addStretch()
    is_picker_active = mode == "class"
    ac = t["secondary"] if is_picker_active else t["hint"]
    tc = t["primary"] if is_picker_active else t["hint"]
    a1 = QPushButton()
    a1.setIcon(qta.icon("ph.caret-left-bold", color=ac))
    a1.setIconSize(QSize(14, 14))
    a1.setFixedSize(22, 22)
    a1.setStyleSheet("background: transparent; border: none;")
    dr.addWidget(a1)
    sl = QLabel("1:00:00")
    sl.setStyleSheet(f"color: {tc}; font-size: 18px; font-weight: 400;")
    dr.addWidget(sl)
    a2 = QPushButton()
    a2.setIcon(qta.icon("ph.caret-right-bold", color=ac))
    a2.setIconSize(QSize(14, 14))
    a2.setFixedSize(22, 22)
    a2.setStyleSheet("background: transparent; border: none;")
    dr.addWidget(a2)
    dr.addStretch()
    root.addLayout(dr)
    root.addSpacing(12)

    # Tiers
    if mode == "quick":
        active_set = {"5m"}
        rows = [["30s", "1m", "2m", "5m"], ["10m", "15m", "30m", "1h"]]
    else:
        active_set = {"1m", "5m", "10m"}
        rows = [["30s", "1m", "3m", "5m"], ["10m", "15m", "30m", "1h"]]
    for labels in rows:
        tr = QHBoxLayout()
        tr.setContentsMargins(0, 0, 0, 0)
        tr.setSpacing(3)
        for lb in labels:
            pb = QPushButton(lb)
            pb.setStyleSheet((BTN_ACTIVE if lb in active_set else BTN_INACTIVE).format(**t))
            tr.addWidget(pb)
        tr.addStretch()
        root.addLayout(tr)
        root.addSpacing(3)

    root.addSpacing(6)
    if mode == "quick":
        sm = QLabel("11 img x 5:00")
    else:
        sm = QLabel("2x1m 3x5m 2x10m")
    sm.setStyleSheet(f"color: {t['secondary']}; font-size: 9px;")
    root.addWidget(sm)
    root.addSpacing(2)
    if mode == "quick":
        tot = QLabel("0:55:00")
    else:
        tot = QLabel("0:37:00")
    tot.setStyleSheet(f"color: {t['primary']}; font-size: 10px;")
    root.addWidget(tot)
    root.addStretch()

    bot = QHBoxLayout()
    bot.setContentsMargins(0, 0, 0, 0)
    bot.setSpacing(6)
    dice = _icon_toggle(t, "ph.dice-five-fill", "ph.dice-three-bold", dice_on, size=34)
    bot.addWidget(dice, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
    bot.addStretch()
    bot.addWidget(_start_btn(t), alignment=Qt.AlignmentFlag.AlignBottom)
    root.addLayout(bot)
    return panel


def _editor_list(t, show_reserve=True):
    editor = QWidget()
    editor.setFixedSize(EDITOR_W, COMPACT_H)
    editor.setStyleSheet(f"background-color: {t['bg']};")
    el = QVBoxLayout(editor)
    el.setContentsMargins(6, 6, 6, 8)
    el.setSpacing(3)

    tb = QHBoxLayout()
    tb.setSpacing(3)
    for ic in ["ph.file-plus-bold", "ph.folder-plus-bold", "ph.link-bold"]:
        b = QPushButton()
        b.setIcon(qta.icon(ic, color=t["btn_text"]))
        b.setIconSize(QSize(11, 11))
        b.setFixedSize(20, 18)
        b.setStyleSheet(f"background-color: {t['btn']}; border: 1px solid {t['border']};")
        tb.addWidget(b)
    tb.addStretch()
    for ic in ["ph.arrow-square-out-bold", "ph.eraser-bold", "ph.x-bold"]:
        b = QPushButton()
        b.setIcon(qta.icon(ic, color=t["btn_text"]))
        b.setIconSize(QSize(11, 11))
        b.setFixedSize(20, 18)
        b.setStyleSheet(f"background-color: {t['btn']}; border: 1px solid {t['border']};")
        tb.addWidget(b)
    el.addLayout(tb)

    cnt = QLabel("IMAGES — 11")
    cnt.setStyleSheet(f"color: {t['secondary']}; font-size: 8px; font-weight: 500; letter-spacing: 1px;")
    el.addWidget(cnt)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setStyleSheet(
        f"QScrollArea {{ background-color: {t['bg2']}; border: 1px dashed {t['border']}; }}"
        f"QWidget {{ background-color: {t['bg2']}; }}")
    la = QWidget()
    ll = QVBoxLayout(la)
    ll.setContentsMargins(2, 2, 2, 2)
    ll.setSpacing(1)
    ll.addWidget(_group_header(t, "1m", 2))
    ll.addWidget(_file_row(t, 1, "portrait_001.jpg", "1:00"))
    ll.addWidget(_file_row(t, 2, "portrait_002.jpg", "1:00", pinned=True))
    ll.addWidget(_group_header(t, "5m", 3))
    ll.addWidget(_file_row(t, 3, "gesture_001.jpg", "5:00"))
    ll.addWidget(_file_row(t, 4, "gesture_002.jpg", "5:00"))
    ll.addWidget(_file_row(t, 5, "gesture_003.jpg", "5:00", pinned=True))
    ll.addWidget(_group_header(t, "10m", 2))
    ll.addWidget(_file_row(t, 6, "anatomy_001.jpg", "10:00"))
    ll.addWidget(_file_row(t, 7, "anatomy_002.jpg", "10:00"))
    if show_reserve:
        ll.addWidget(_group_header(t, "Reserve", 4, inactive=True))
        for i, n in enumerate(["extra_001", "extra_002", "extra_003", "extra_004"], 8):
            ll.addWidget(_file_row_reserve(t, i, f"{n}.jpg"))
    ll.addStretch()
    scroll.setWidget(la)
    el.addWidget(scroll, 1)

    bot = QHBoxLayout()
    bot.setSpacing(3)
    for i, ic in enumerate(["ph.list-bullets-bold", "ph.squares-four-bold"]):
        b = QPushButton()
        b.setIcon(qta.icon(ic, color=t["primary"] if i == 0 else t["btn_text"]))
        b.setIconSize(QSize(11, 11))
        b.setFixedSize(18, 18)
        b.setStyleSheet(
            (f"background-color: {t['active']}; border: 1px solid {t['accent']};" if i == 0
             else f"background-color: {t['btn']}; border: 1px solid {t['border']};"))
        bot.addWidget(b)
    zl = QLabel("Zoom:")
    zl.setStyleSheet(f"color: {t['hint']}; font-size: 8px;")
    bot.addWidget(zl)
    zs = QSlider(Qt.Orientation.Horizontal)
    zs.setFixedWidth(35)
    zs.setStyleSheet(
        f"QSlider::groove:horizontal {{ background: {t['border']}; height: 3px; }}"
        f"QSlider::handle:horizontal {{ background: {t['secondary']}; width: 8px; margin: -3px 0; }}")
    bot.addWidget(zs)
    bot.addStretch()
    cb = QPushButton()
    cb.setIcon(qta.icon("ph.trash-bold", color=t["hint"]))
    cb.setIconSize(QSize(9, 9))
    cb.setFixedSize(14, 14)
    cb.setStyleSheet("background: transparent; border: none; padding: 0px;")
    bot.addWidget(cb)
    cl = QLabel("12MB")
    cl.setStyleSheet(f"color: {t['hint']}; font-size: 8px;")
    bot.addWidget(cl)
    el.addLayout(bot)

    tot = QLabel("1:07:00 / 1:00:00" if show_reserve else "0:37:00")
    tot.setStyleSheet(f"color: {t['warning'] if show_reserve else t['primary']}; font-size: 9px;")
    el.addWidget(tot)
    return editor


def _editor_grid(t):
    editor = QWidget()
    editor.setFixedSize(EDITOR_W, COMPACT_H)
    editor.setStyleSheet(f"background-color: {t['bg']};")
    el = QVBoxLayout(editor)
    el.setContentsMargins(6, 6, 6, 8)
    el.setSpacing(3)

    tb = QHBoxLayout()
    tb.setSpacing(3)
    for ic in ["ph.file-plus-bold", "ph.folder-plus-bold", "ph.link-bold"]:
        b = QPushButton()
        b.setIcon(qta.icon(ic, color=t["btn_text"]))
        b.setIconSize(QSize(11, 11))
        b.setFixedSize(20, 18)
        b.setStyleSheet(f"background-color: {t['btn']}; border: 1px solid {t['border']};")
        tb.addWidget(b)
    tb.addStretch()
    for ic in ["ph.arrow-square-out-bold", "ph.eraser-bold", "ph.x-bold"]:
        b = QPushButton()
        b.setIcon(qta.icon(ic, color=t["btn_text"]))
        b.setIconSize(QSize(11, 11))
        b.setFixedSize(20, 18)
        b.setStyleSheet(f"background-color: {t['btn']}; border: 1px solid {t['border']};")
        tb.addWidget(b)
    el.addLayout(tb)

    cnt = QLabel("IMAGES — 11")
    cnt.setStyleSheet(f"color: {t['secondary']}; font-size: 8px; font-weight: 500; letter-spacing: 1px;")
    el.addWidget(cnt)

    g_scroll = QScrollArea()
    g_scroll.setWidgetResizable(True)
    g_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    g_scroll.setStyleSheet(
        f"QScrollArea {{ background-color: {t['bg2']}; border: 1px dashed {t['border']}; }}"
        f"QWidget {{ background-color: {t['bg2']}; }}")
    ga = QWidget()
    gl = QVBoxLayout(ga)
    gl.setContentsMargins(4, 4, 4, 4)
    gl.setSpacing(3)

    gl.addWidget(_group_header(t, "1m", 2))
    r1 = QHBoxLayout()
    r1.setSpacing(3)
    r1.addWidget(_tile(t))
    r1.addWidget(_tile(t, pinned=True))
    r1.addStretch()
    gl.addLayout(r1)

    gl.addWidget(_group_header(t, "5m", 3))
    r2 = QHBoxLayout()
    r2.setSpacing(3)
    r2.addWidget(_tile(t))
    r2.addWidget(_tile(t))
    r2.addWidget(_tile(t, pinned=True))
    r2.addStretch()
    gl.addLayout(r2)

    gl.addWidget(_group_header(t, "10m", 2))
    r3 = QHBoxLayout()
    r3.setSpacing(3)
    r3.addWidget(_tile(t))
    r3.addWidget(_tile(t))
    r3.addStretch()
    gl.addLayout(r3)

    gl.addWidget(_group_header(t, "Reserve", 4, inactive=True))
    r4 = QHBoxLayout()
    r4.setSpacing(3)
    for _ in range(4):
        r4.addWidget(_tile(t, reserve=True))
    r4.addStretch()
    gl.addLayout(r4)

    gl.addStretch()
    g_scroll.setWidget(ga)
    el.addWidget(g_scroll, 1)

    bot = QHBoxLayout()
    bot.setSpacing(3)
    for i, ic in enumerate(["ph.list-bullets-bold", "ph.squares-four-bold"]):
        b = QPushButton()
        b.setIcon(qta.icon(ic, color=t["primary"] if i == 1 else t["btn_text"]))
        b.setIconSize(QSize(11, 11))
        b.setFixedSize(18, 18)
        b.setStyleSheet(
            (f"background-color: {t['active']}; border: 1px solid {t['accent']};" if i == 1
             else f"background-color: {t['btn']}; border: 1px solid {t['border']};"))
        bot.addWidget(b)
    zl = QLabel("Zoom:")
    zl.setStyleSheet(f"color: {t['hint']}; font-size: 8px;")
    bot.addWidget(zl)
    zs = QSlider(Qt.Orientation.Horizontal)
    zs.setFixedWidth(35)
    zs.setStyleSheet(
        f"QSlider::groove:horizontal {{ background: {t['border']}; height: 3px; }}"
        f"QSlider::handle:horizontal {{ background: {t['secondary']}; width: 8px; margin: -3px 0; }}")
    bot.addWidget(zs)
    bot.addStretch()
    cb = QPushButton()
    cb.setIcon(qta.icon("ph.trash-bold", color=t["hint"]))
    cb.setIconSize(QSize(9, 9))
    cb.setFixedSize(14, 14)
    cb.setStyleSheet("background: transparent; border: none; padding: 0px;")
    bot.addWidget(cb)
    cl = QLabel("12MB")
    cl.setStyleSheet(f"color: {t['hint']}; font-size: 8px;")
    bot.addWidget(cl)
    el.addLayout(bot)

    tot = QLabel("1:07:00 / 1:00:00")
    tot.setStyleSheet(f"color: {t['warning']}; font-size: 9px;")
    el.addWidget(tot)
    return editor


def _combine(settings, editor, t):
    w = QWidget()
    w.setFixedSize(COMPACT_W + 1 + EDITOR_W, COMPACT_H)
    w.setStyleSheet(f"background-color: {t['bg']};")
    root = QHBoxLayout(w)
    root.setContentsMargins(0, 0, 0, 0)
    root.setSpacing(0)
    root.addWidget(settings)
    div = QFrame()
    div.setFrameShape(QFrame.Shape.VLine)
    div.setStyleSheet(f"color: {t['border']};")
    div.setFixedWidth(1)
    root.addWidget(div)
    root.addWidget(editor)
    return w


def main():
    app = QApplication(sys.argv)

    # 4 combos: dark class+list, dark quick+grid, light class+list, light quick+grid
    widgets = [
        _combine(_settings_panel(DARK, "class", True, False),
                 _editor_list(DARK, show_reserve=True), DARK),
        _combine(_settings_panel(DARK, "quick", False, False),
                 _editor_grid(DARK), DARK),
        _combine(_settings_panel(LIGHT, "class", True, False),
                 _editor_list(LIGHT, show_reserve=True), LIGHT),
        _combine(_settings_panel(LIGHT, "quick", False, False),
                 _editor_grid(LIGHT), LIGHT),
    ]
    for w in widgets:
        w.show()

    def capture():
        pixmaps = [w.grab() for w in widgets]
        gap = 10

        # 2x2 grid
        pw = pixmaps[0].width()
        ph = pixmaps[0].height()
        total_w = pw * 2 + gap * 3
        total_h = ph * 2 + gap * 3

        result = QPixmap(total_w, total_h)
        result.fill(QColor("#111"))
        p = QPainter(result)
        p.drawPixmap(gap, gap, pixmaps[0])
        p.drawPixmap(gap + pw + gap, gap, pixmaps[1])
        p.drawPixmap(gap, gap + ph + gap, pixmaps[2])
        p.drawPixmap(gap + pw + gap, gap + ph + gap, pixmaps[3])
        p.end()
        result.save("mockup_full.png")
        print("Saved mockup_full.png")
        app.quit()

    QTimer.singleShot(300, capture)
    app.exec()

if __name__ == "__main__":
    main()
