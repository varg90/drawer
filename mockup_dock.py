"""Dock variants: main window FIXED, editor adapts to main."""
import sys
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                              QLabel, QPushButton, QFrame, QSlider)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QPixmap, QPainter, QColor
import qtawesome as qta

ICON = "fa6s.pencil"
ICON_RATIO = 0.75
RADIUS_RATIO = 0.12
M = 14
M_BOT = 18
COMPACT_W = 250
COMPACT_H = 290
START_SZ = 42
EDITOR_W_SIDE = 250  # same as main width
EDITOR_H_BOTTOM = 320  # fixed height when docked bottom

DARK = {
    "bg": "#191919", "bg2": "#171717", "btn": "#222222",
    "active": "#333b3a", "border": "#303030", "accent": "#4a7d74",
    "primary": "#ddd", "secondary": "#606060", "hint": "#454545",
    "header": "#84a39e", "btn_text": "#84a39e", "start_text": "#252525",
    "warning": "#cc5555",
}

BTN_STYLE_ACTIVE = (
    "background-color: {active}; color: {primary}; "
    "border: 1px solid {accent}; font-size: 10px; padding: 4px 7px;")
BTN_STYLE_INACTIVE = (
    "background-color: {btn}; color: {secondary}; "
    "border: 1px solid {border}; font-size: 10px; padding: 4px 7px;")


def _start_btn(t, size=START_SZ):
    btn = QPushButton()
    icon_sz = int(size * ICON_RATIO)
    radius = int(size * RADIUS_RATIO)
    btn.setIcon(qta.icon(ICON, color=t["start_text"]))
    btn.setIconSize(QSize(icon_sz, icon_sz))
    btn.setFixedSize(size, size)
    btn.setStyleSheet(
        f"background-color: {t['accent']}; border: none; border-radius: {radius}px;")
    return btn


def _icon_toggle(t, icon_on, icon_off, is_on, size=13):
    btn = QPushButton()
    icon_name = icon_on if is_on else icon_off
    color = t["accent"] if is_on else t["hint"]
    btn.setIcon(qta.icon(icon_name, color=color))
    btn.setIconSize(QSize(size, size))
    btn.setFixedSize(size, size)
    btn.setStyleSheet("background: transparent; border: none; padding: 0px;")
    return btn


def _group_header(t, label, count, inactive=False):
    btn = QPushButton(f"  {label} — {count}")
    btn.setStyleSheet(
        f"background-color: {t['btn']}; "
        f"color: {t['hint'] if inactive else t['secondary']}; "
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
    time_lbl = QLabel(timer)
    time_lbl.setStyleSheet(f"color: {t['secondary']}; font-size: 9px; background: transparent;")
    row.addWidget(time_lbl)
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


def _settings_panel(t, tag_text=""):
    panel = QWidget()
    panel.setFixedSize(COMPACT_W, COMPACT_H)
    panel.setStyleSheet(f"background-color: {t['bg']};")
    root = QVBoxLayout(panel)
    root.setContentsMargins(M, M, M, M_BOT)
    root.setSpacing(0)

    if tag_text:
        tag = QLabel(tag_text)
        tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tag.setStyleSheet(f"color: {t['hint']}; font-size: 8px;")
        root.addWidget(tag)

    header = QHBoxLayout()
    header.setContentsMargins(0, 0, 0, 0)
    header.setSpacing(0)
    left_hdr = QHBoxLayout()
    left_hdr.setSpacing(2)
    left_hdr.setContentsMargins(0, 0, 0, 0)
    info = QPushButton()
    info.setIcon(qta.icon("ph.info-bold", color=t["hint"]))
    info.setIconSize(QSize(13, 13))
    info.setFixedSize(13, 13)
    info.setStyleSheet("background: transparent; border: none; padding: 0px;")
    left_hdr.addWidget(info)
    left_hdr.addWidget(_icon_toggle(t, "ph.push-pin-fill", "ph.push-pin-bold", False))
    left_hdr.addStretch()
    lw = QWidget()
    lw.setLayout(left_hdr)
    lw.setStyleSheet("background: transparent;")
    right_hdr = QHBoxLayout()
    right_hdr.setSpacing(2)
    right_hdr.setContentsMargins(0, 0, 0, 0)
    right_hdr.addStretch()
    accent_dot = QPushButton()
    accent_dot.setFixedSize(11, 11)
    accent_dot.setStyleSheet(
        f"background-color: {t['accent']}; border: 1px solid {t['border']}; "
        f"border-radius: 5px; padding: 0px;")
    right_hdr.addWidget(accent_dot)
    moon = QPushButton()
    moon.setIcon(qta.icon("ph.moon-bold", color=t["hint"]))
    moon.setIconSize(QSize(13, 13))
    moon.setFixedSize(13, 13)
    moon.setStyleSheet("background: transparent; border: none; padding: 0px;")
    right_hdr.addWidget(moon)
    rw = QWidget()
    rw.setLayout(right_hdr)
    rw.setStyleSheet("background: transparent;")
    title = QLabel("REFBOT")
    title.setAlignment(Qt.AlignmentFlag.AlignCenter)
    title.setStyleSheet(
        f"color: {t['header']}; font-size: 11px; font-weight: 500; letter-spacing: 3px;")
    header.addWidget(lw, 1)
    header.addWidget(title)
    header.addWidget(rw, 1)
    root.addLayout(header)
    root.addSpacing(6)

    mode_row = QHBoxLayout()
    mode_row.setContentsMargins(0, 0, 0, 0)
    mode_row.setSpacing(0)
    for lb, is_active in [("Class", True), ("Quick", False)]:
        b = QPushButton(lb)
        s = t['active'] if is_active else t['bg']
        c = t['primary'] if is_active else t['secondary']
        b.setStyleSheet(
            f"background-color: {s}; color: {c}; "
            f"border: 1px solid {t['border']}; font-size: 10px; font-weight: 500; padding: 3px 7px;")
        mode_row.addWidget(b)
    mode_row.addStretch()
    count = QLabel("11 img")
    count.setStyleSheet(f"color: {t['secondary']}; font-size: 10px;")
    mode_row.addWidget(count)
    mode_row.addSpacing(2)
    add = QPushButton()
    add.setIcon(qta.icon("ph.plus-bold", color=t["btn_text"]))
    add.setIconSize(QSize(12, 12))
    add.setFixedSize(20, 20)
    add.setStyleSheet(f"background-color: {t['btn']}; border: 1px solid {t['border']};")
    mode_row.addWidget(add)
    root.addLayout(mode_row)
    root.addSpacing(10)

    dur_row = QHBoxLayout()
    dur_row.addStretch()
    arr1 = QPushButton()
    arr1.setIcon(qta.icon("ph.caret-left-bold", color=t["secondary"]))
    arr1.setIconSize(QSize(14, 14))
    arr1.setFixedSize(22, 22)
    arr1.setStyleSheet("background: transparent; border: none;")
    dur_row.addWidget(arr1)
    ses = QLabel("1:00:00")
    ses.setStyleSheet(f"color: {t['primary']}; font-size: 18px; font-weight: 400;")
    dur_row.addWidget(ses)
    arr2 = QPushButton()
    arr2.setIcon(qta.icon("ph.caret-right-bold", color=t["secondary"]))
    arr2.setIconSize(QSize(14, 14))
    arr2.setFixedSize(22, 22)
    arr2.setStyleSheet("background: transparent; border: none;")
    dur_row.addWidget(arr2)
    dur_row.addStretch()
    root.addLayout(dur_row)
    root.addSpacing(12)

    active_set = {"1m", "5m", "10m"}
    for tier_labels in [["30s", "1m", "3m", "5m"], ["10m", "15m", "30m", "1h"]]:
        tr = QHBoxLayout()
        tr.setContentsMargins(0, 0, 0, 0)
        tr.setSpacing(3)
        for lb in tier_labels:
            pb = QPushButton(lb)
            if lb in active_set:
                pb.setStyleSheet(BTN_STYLE_ACTIVE.format(**t))
            else:
                pb.setStyleSheet(BTN_STYLE_INACTIVE.format(**t))
            tr.addWidget(pb)
        tr.addStretch()
        root.addLayout(tr)
        root.addSpacing(3)

    root.addSpacing(6)
    dist = QLabel("2x1m 3x5m 2x10m")
    dist.setStyleSheet(f"color: {t['secondary']}; font-size: 9px;")
    root.addWidget(dist)
    root.addSpacing(2)
    total = QLabel("0:37:00")
    total.setStyleSheet(f"color: {t['primary']}; font-size: 10px;")
    root.addWidget(total)
    root.addStretch()

    bot = QHBoxLayout()
    bot.setContentsMargins(0, 0, 0, 0)
    bot.setSpacing(6)
    dice = _icon_toggle(t, "ph.dice-five-fill", "ph.dice-three-bold", True, size=34)
    bot.addWidget(dice, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
    bot.addStretch()
    bot.addWidget(_start_btn(t), alignment=Qt.AlignmentFlag.AlignBottom)
    root.addLayout(bot)
    return panel


def _editor_content(t, layout):
    """Populate editor layout with groups, files, controls."""
    tb = QHBoxLayout()
    tb.setSpacing(3)
    for icon_name in ["ph.file-plus-bold", "ph.folder-plus-bold", "ph.link-bold"]:
        b = QPushButton()
        b.setIcon(qta.icon(icon_name, color=t["btn_text"]))
        b.setIconSize(QSize(11, 11))
        b.setFixedSize(20, 18)
        b.setStyleSheet(f"background-color: {t['btn']}; border: 1px solid {t['border']};")
        tb.addWidget(b)
    tb.addStretch()
    detach = QPushButton()
    detach.setIcon(qta.icon("ph.arrow-square-out-bold", color=t["btn_text"]))
    detach.setIconSize(QSize(11, 11))
    detach.setFixedSize(20, 18)
    detach.setStyleSheet(f"background-color: {t['btn']}; border: 1px solid {t['border']};")
    tb.addWidget(detach)
    eraser = QPushButton()
    eraser.setIcon(qta.icon("ph.eraser-bold", color=t["btn_text"]))
    eraser.setIconSize(QSize(11, 11))
    eraser.setFixedSize(20, 18)
    eraser.setStyleSheet(f"background-color: {t['btn']}; border: 1px solid {t['border']};")
    tb.addWidget(eraser)
    close_btn = QPushButton()
    close_btn.setIcon(qta.icon("ph.x-bold", color=t["btn_text"]))
    close_btn.setIconSize(QSize(11, 11))
    close_btn.setFixedSize(20, 18)
    close_btn.setStyleSheet(f"background-color: {t['btn']}; border: 1px solid {t['border']};")
    tb.addWidget(close_btn)
    layout.addLayout(tb)

    cnt = QLabel("IMAGES — 11")
    cnt.setStyleSheet(f"color: {t['secondary']}; font-size: 8px; font-weight: 500; letter-spacing: 1px;")
    layout.addWidget(cnt)

    list_area = QWidget()
    list_area.setStyleSheet(f"background-color: {t['bg2']}; border: 1px dashed {t['border']};")
    la = QVBoxLayout(list_area)
    la.setContentsMargins(2, 2, 2, 2)
    la.setSpacing(1)

    la.addWidget(_group_header(t, "1m", 2))
    la.addWidget(_file_row(t, 1, "portrait_001.jpg", "1:00"))
    la.addWidget(_file_row(t, 2, "portrait_002.jpg", "1:00", pinned=True))
    la.addWidget(_group_header(t, "5m", 3))
    la.addWidget(_file_row(t, 3, "gesture_001.jpg", "5:00"))
    la.addWidget(_file_row(t, 4, "gesture_002.jpg", "5:00"))
    la.addWidget(_file_row(t, 5, "gesture_003.jpg", "5:00", pinned=True))
    la.addWidget(_group_header(t, "10m", 2))
    la.addWidget(_file_row(t, 6, "anatomy_001.jpg", "10:00"))
    la.addWidget(_file_row(t, 7, "anatomy_002.jpg", "10:00"))
    la.addWidget(_group_header(t, "Reserve", 4, inactive=True))
    la.addWidget(_file_row_reserve(t, 8, "extra_001.jpg"))
    la.addWidget(_file_row_reserve(t, 9, "extra_002.jpg"))
    la.addWidget(_file_row_reserve(t, 10, "extra_003.jpg"))
    la.addWidget(_file_row_reserve(t, 11, "extra_004.jpg"))
    la.addStretch()
    layout.addWidget(list_area, 1)

    bot = QHBoxLayout()
    bot.setSpacing(3)
    for i, icon_name in enumerate(["ph.list-bullets-bold", "ph.squares-four-bold"]):
        b = QPushButton()
        b.setIcon(qta.icon(icon_name, color=t["primary"] if i == 0 else t["btn_text"]))
        b.setIconSize(QSize(11, 11))
        b.setFixedSize(18, 18)
        active_s = f"background-color: {t['active']}; border: 1px solid {t['accent']};"
        inactive_s = f"background-color: {t['btn']}; border: 1px solid {t['border']};"
        b.setStyleSheet(active_s if i == 0 else inactive_s)
        bot.addWidget(b)
    zoom_lbl = QLabel("Zoom:")
    zoom_lbl.setStyleSheet(f"color: {t['hint']}; font-size: 8px;")
    bot.addWidget(zoom_lbl)
    zoom = QSlider(Qt.Orientation.Horizontal)
    zoom.setFixedWidth(40)
    zoom.setStyleSheet(
        f"QSlider::groove:horizontal {{ background: {t['border']}; height: 3px; }}"
        f"QSlider::handle:horizontal {{ background: {t['secondary']}; width: 8px; margin: -3px 0; }}")
    bot.addWidget(zoom)
    bot.addStretch()
    cache_btn = QPushButton()
    cache_btn.setIcon(qta.icon("ph.trash-bold", color=t["hint"]))
    cache_btn.setIconSize(QSize(9, 9))
    cache_btn.setFixedSize(14, 14)
    cache_btn.setStyleSheet("background: transparent; border: none; padding: 0px;")
    bot.addWidget(cache_btn)
    cache_lbl = QLabel("12MB")
    cache_lbl.setStyleSheet(f"color: {t['hint']}; font-size: 8px;")
    bot.addWidget(cache_lbl)
    layout.addLayout(bot)

    total = QLabel("1:07:00 / 1:00:00")
    total.setStyleSheet(f"color: {t['warning']}; font-size: 9px;")
    layout.addWidget(total)


def _build_right(t):
    """A) Editor docked right — same height as main."""
    w = QWidget()
    w.setFixedSize(COMPACT_W + 1 + EDITOR_W_SIDE, COMPACT_H)
    w.setStyleSheet(f"background-color: {t['bg']};")
    root = QHBoxLayout(w)
    root.setContentsMargins(0, 0, 0, 0)
    root.setSpacing(0)
    root.addWidget(_settings_panel(t, "A) Right"))
    div = QFrame()
    div.setFrameShape(QFrame.Shape.VLine)
    div.setStyleSheet(f"color: {t['border']};")
    div.setFixedWidth(1)
    root.addWidget(div)
    editor = QWidget()
    editor.setFixedSize(EDITOR_W_SIDE, COMPACT_H)
    el = QVBoxLayout(editor)
    el.setContentsMargins(6, 6, 6, 8)
    el.setSpacing(3)
    _editor_content(t, el)
    root.addWidget(editor)
    return w


def _build_bottom(t):
    """B) Editor docked bottom — same width as main."""
    w = QWidget()
    w.setFixedSize(COMPACT_W, COMPACT_H + 1 + EDITOR_H_BOTTOM)
    w.setStyleSheet(f"background-color: {t['bg']};")
    root = QVBoxLayout(w)
    root.setContentsMargins(0, 0, 0, 0)
    root.setSpacing(0)
    root.addWidget(_settings_panel(t, "B) Bottom"))
    div = QFrame()
    div.setFrameShape(QFrame.Shape.HLine)
    div.setStyleSheet(f"color: {t['border']};")
    div.setFixedHeight(1)
    root.addWidget(div)
    editor = QWidget()
    editor.setFixedSize(COMPACT_W, EDITOR_H_BOTTOM)
    el = QVBoxLayout(editor)
    el.setContentsMargins(6, 6, 6, 8)
    el.setSpacing(3)
    _editor_content(t, el)
    root.addWidget(editor)
    return w


def _build_detached(t):
    """C) Detached — separate free-size window."""
    settings = _settings_panel(t, "C) Detached")

    editor_win = QWidget()
    editor_win.setFixedSize(320, 400)
    editor_win.setStyleSheet(f"background-color: {t['bg']};")
    ewl = QVBoxLayout(editor_win)
    ewl.setContentsMargins(0, 0, 0, 0)
    ewl.setSpacing(0)

    title_bar = QHBoxLayout()
    title_bar.setContentsMargins(8, 5, 8, 3)
    title_bar.setSpacing(4)
    win_title = QLabel("Images")
    win_title.setStyleSheet(f"color: {t['secondary']}; font-size: 10px; font-weight: 500;")
    title_bar.addWidget(win_title)
    title_bar.addStretch()
    dock_btn = QPushButton()
    dock_btn.setIcon(qta.icon("ph.arrows-in-bold", color=t["btn_text"]))
    dock_btn.setIconSize(QSize(12, 12))
    dock_btn.setFixedSize(22, 20)
    dock_btn.setStyleSheet(f"background-color: {t['btn']}; border: 1px solid {t['border']};")
    title_bar.addWidget(dock_btn)
    ewl.addLayout(title_bar)

    content = QWidget()
    cl = QVBoxLayout(content)
    cl.setContentsMargins(8, 4, 8, 8)
    cl.setSpacing(3)
    _editor_content(t, cl)
    ewl.addWidget(content, 1)

    return settings, editor_win


def main():
    app = QApplication(sys.argv)
    t = DARK

    right = _build_right(t)
    bottom = _build_bottom(t)
    settings_c, editor_c = _build_detached(t)

    all_widgets = [right, bottom, settings_c, editor_c]
    for w in all_widgets:
        w.show()

    def capture():
        right_pix = right.grab()
        bottom_pix = bottom.grab()
        settings_pix = settings_c.grab()
        editor_pix = editor_c.grab()

        gap = 10
        spacer = 15

        # Row 1: docked right
        r1_h = right_pix.height()

        # Row 2: docked bottom + detached pair
        r2_left_h = bottom_pix.height()
        r2_right_h = max(settings_pix.height(), editor_pix.height())
        r2_h = max(r2_left_h, r2_right_h)

        r2_right_w = settings_pix.width() + spacer + editor_pix.width()
        total_w = max(
            right_pix.width() + gap * 2,
            bottom_pix.width() + gap * 3 + r2_right_w
        )
        total_h = r1_h + r2_h + gap * 3

        result = QPixmap(total_w, total_h)
        result.fill(QColor("#111"))
        p = QPainter(result)

        p.drawPixmap(gap, gap, right_pix)

        y2 = r1_h + gap * 2
        p.drawPixmap(gap, y2, bottom_pix)
        det_x = gap + bottom_pix.width() + gap * 2
        p.drawPixmap(det_x, y2, settings_pix)
        p.drawPixmap(det_x + settings_pix.width() + spacer, y2, editor_pix)

        p.end()
        result.save("mockup_dock.png")
        print("Saved mockup_dock.png")
        app.quit()

    QTimer.singleShot(300, capture)
    app.exec()

if __name__ == "__main__":
    main()
