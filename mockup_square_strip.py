"""v10: pixel-perfect alignment — all edges flush with margins."""
import sys
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                              QLabel, QPushButton, QFrame,
                              QListWidget, QListWidgetItem)
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
DUR_ROW_H = 40
START_SZ = 42

DARK = {
    "bg": "#191919", "bg2": "#171717", "btn": "#222222",
    "active": "#333b3a", "border": "#303030", "accent": "#4a7d74",
    "primary": "#ddd", "secondary": "#606060", "hint": "#454545",
    "header": "#84a39e", "btn_text": "#84a39e", "start_text": "#252525",
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


def _icon_toggle(t, icon_on, icon_off, is_on, size=20):
    btn = QPushButton()
    icon_name = icon_on if is_on else icon_off
    color = t["accent"] if is_on else t["hint"]
    btn.setIcon(qta.icon(icon_name, color=color))
    btn.setIconSize(QSize(size, size))
    btn.setFixedSize(size, size)
    btn.setStyleSheet("background: transparent; border: none; padding: 0px;")
    return btn


def _timer_btn(t, label, is_active):
    pb = QPushButton(label)
    if is_active:
        pb.setStyleSheet(BTN_STYLE_ACTIVE.format(**t))
    else:
        pb.setStyleSheet(BTN_STYLE_INACTIVE.format(**t))
    return pb


def _build_settings_panel(t, mode="quick", dice_on=False, pin_on=False, tag_text=""):
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

    # === HEADER — balanced containers, compact spacing ===
    header = QHBoxLayout()
    header.setContentsMargins(0, 0, 0, 0)
    header.setSpacing(0)

    # Left: info + pin, flush to left margin
    left_hdr = QHBoxLayout()
    left_hdr.setSpacing(2)
    left_hdr.setContentsMargins(0, 0, 0, 0)
    info = QPushButton()
    info.setIcon(qta.icon("ph.info-bold", color=t["hint"]))
    info.setIconSize(QSize(13, 13))
    info.setFixedSize(13, 13)
    info.setStyleSheet("background: transparent; border: none; padding: 0px;")
    left_hdr.addWidget(info)
    pin = _icon_toggle(t, "ph.push-pin-fill", "ph.push-pin-bold", pin_on, size=13)
    left_hdr.addWidget(pin)
    left_hdr.addStretch()
    lw = QWidget()
    lw.setLayout(left_hdr)
    lw.setStyleSheet("background: transparent;")

    # Right: accent + moon, flush to right margin, same 18px size
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

    # === MODE TOGGLE + COUNT + ADD — compact spacing matching header ===
    mode_row = QHBoxLayout()
    mode_row.setContentsMargins(0, 0, 0, 0)
    mode_row.setSpacing(0)
    for lb, key in [("Class", "class"), ("Quick", "quick")]:
        b = QPushButton(lb)
        is_active = key == mode
        s = t['active'] if is_active else t['bg']
        c = t['primary'] if is_active else t['secondary']
        b.setStyleSheet(
            f"background-color: {s}; color: {c}; "
            f"border: 1px solid {t['border']}; font-size: 10px; font-weight: 500; padding: 3px 7px;")
        mode_row.addWidget(b)
    mode_row.addStretch()
    count = QLabel("12 img")
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

    # === SLOT A: Duration picker ===
    slot_a = QWidget()
    slot_a.setFixedHeight(DUR_ROW_H)
    slot_a.setStyleSheet("background: transparent;")
    sa_layout = QHBoxLayout(slot_a)
    sa_layout.setContentsMargins(0, 0, 0, 0)

    is_active_picker = mode == "class"
    arrow_color = t["secondary"] if is_active_picker else t["hint"]
    time_color = t["primary"] if is_active_picker else t["hint"]

    sa_layout.addStretch()
    left_arr = QPushButton()
    left_arr.setIcon(qta.icon("ph.caret-left-bold", color=arrow_color))
    left_arr.setIconSize(QSize(14, 14))
    left_arr.setFixedSize(22, 22)
    left_arr.setStyleSheet("background: transparent; border: none;")
    if not is_active_picker:
        left_arr.setEnabled(False)
    sa_layout.addWidget(left_arr)
    ses = QLabel("1:00:00")
    ses.setStyleSheet(f"color: {time_color}; font-size: 18px; font-weight: 400;")
    sa_layout.addWidget(ses)
    right_arr = QPushButton()
    right_arr.setIcon(qta.icon("ph.caret-right-bold", color=arrow_color))
    right_arr.setIconSize(QSize(14, 14))
    right_arr.setFixedSize(22, 22)
    right_arr.setStyleSheet("background: transparent; border: none;")
    if not is_active_picker:
        right_arr.setEnabled(False)
    sa_layout.addWidget(right_arr)
    sa_layout.addStretch()
    root.addWidget(slot_a)
    root.addSpacing(12)

    # === SLOT B: Timer buttons ===
    if mode == "quick":
        active_set = {"5m"}
        for row_labels in [["30s", "1m", "2m", "5m"], ["10m", "15m", "30m", "1h"]]:
            pr = QHBoxLayout()
            pr.setContentsMargins(0, 0, 0, 0)
            pr.setSpacing(3)
            for pl in row_labels:
                pr.addWidget(_timer_btn(t, pl, pl in active_set))
            pr.addStretch()
            root.addLayout(pr)
            root.addSpacing(3)
    else:
        active_set = {"1m", "5m", "10m"}
        for tier_labels in [["30s", "1m", "3m", "5m"], ["10m", "15m", "30m", "1h"]]:
            tr = QHBoxLayout()
            tr.setContentsMargins(0, 0, 0, 0)
            tr.setSpacing(3)
            for lb in tier_labels:
                tr.addWidget(_timer_btn(t, lb, lb in active_set))
            tr.addStretch()
            root.addLayout(tr)
            root.addSpacing(3)

    root.addSpacing(6)

    # === SLOT C: Summary ===
    if mode == "quick":
        summary = QLabel("12 img x 5:00")
    else:
        summary = QLabel("4x1m  4x5m  4x10m")
    summary.setStyleSheet(f"color: {t['secondary']}; font-size: 9px;")
    root.addWidget(summary)
    root.addSpacing(2)

    # === SLOT D: Total ===
    if mode == "quick":
        total = QLabel("1:00:00")
    else:
        total = QLabel("0:50:00")
    total.setStyleSheet(f"color: {t['primary']}; font-size: 10px;")
    root.addWidget(total)

    root.addStretch()

    # === BOTTOM BAR — dice left-aligned, start right-aligned, bottom-aligned ===
    bot = QHBoxLayout()
    bot.setContentsMargins(0, 0, 0, 0)
    bot.setSpacing(6)

    dice = _icon_toggle(t, "ph.dice-five-fill", "ph.dice-three-bold", dice_on, size=34)
    bot.addWidget(dice, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
    bot.addStretch()
    bot.addWidget(_start_btn(t), alignment=Qt.AlignmentFlag.AlignBottom)
    root.addLayout(bot)

    return panel


def _build_wide(t, mode="quick", dice_on=False, pin_on=False, tag_text=""):
    w = QWidget()
    w.setFixedSize(COMPACT_W + 280, COMPACT_H)
    w.setStyleSheet(f"background-color: {t['bg']};")
    root = QHBoxLayout(w)
    root.setContentsMargins(0, 0, 0, 0)
    root.setSpacing(0)

    settings = _build_settings_panel(t, mode, dice_on, pin_on, tag_text)
    root.addWidget(settings)

    div = QFrame()
    div.setFrameShape(QFrame.Shape.VLine)
    div.setStyleSheet(f"color: {t['border']};")
    div.setFixedWidth(1)
    root.addWidget(div)

    editor = QWidget()
    el = QVBoxLayout(editor)
    el.setContentsMargins(8, M, 8, M_BOT)
    el.setSpacing(4)

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
    close_btn = QPushButton()
    close_btn.setIcon(qta.icon("ph.x-bold", color=t["btn_text"]))
    close_btn.setIconSize(QSize(12, 12))
    close_btn.setFixedSize(22, 20)
    close_btn.setStyleSheet(f"background-color: {t['btn']}; border: 1px solid {t['border']};")
    tb.addWidget(close_btn)
    el.addLayout(tb)

    cnt = QLabel("IMAGES — 12")
    cnt.setStyleSheet(f"color: {t['secondary']}; font-size: 9px; font-weight: 500; letter-spacing: 1px;")
    el.addWidget(cnt)

    lw = QListWidget()
    lw.setStyleSheet(
        f"QListWidget {{ background-color: {t['bg2']}; border: none; "
        f"font-size: 10px; color: {t['primary']}; }}"
        f"QListWidget::item {{ padding: 2px; }}")
    for i in range(8):
        lw.addItem(QListWidgetItem(f"  {i+1}.  reference_{i+1:03d}.jpg    5:00"))
    el.addWidget(lw, 1)

    vbot = QHBoxLayout()
    vbot.setSpacing(4)
    for icon_name in ["ph.list-bullets-bold", "ph.squares-four-bold"]:
        b = QPushButton()
        b.setIcon(qta.icon(icon_name, color=t["btn_text"]))
        b.setIconSize(QSize(12, 12))
        b.setFixedSize(20, 20)
        b.setStyleSheet(f"background-color: {t['btn']}; border: 1px solid {t['border']};")
        vbot.addWidget(b)
    vbot.addStretch()
    el.addLayout(vbot)

    root.addWidget(editor, 1)
    return w


def main():
    app = QApplication(sys.argv)
    t = DARK

    widgets = [
        _build_settings_panel(t, "class", True, False, "Class — compact"),
        _build_settings_panel(t, "quick", False, False, "Quick — compact"),
        _build_wide(t, "class", True, False, "Class — wide"),
        _build_wide(t, "quick", False, False, "Quick — wide"),
    ]
    for w in widgets:
        w.show()

    def capture():
        pixmaps = [w.grab() for w in widgets]
        gap = 10

        r1_w = pixmaps[0].width() + pixmaps[1].width() + gap * 3
        r1_h = max(pixmaps[0].height(), pixmaps[1].height())
        r2_w = pixmaps[2].width() + gap * 2
        r2_h = pixmaps[2].height()
        r3_w = pixmaps[3].width() + gap * 2
        r3_h = pixmaps[3].height()

        total_w = max(r1_w, r2_w, r3_w)
        total_h = r1_h + r2_h + r3_h + gap * 4

        result = QPixmap(total_w, total_h)
        result.fill(QColor("#111"))
        p = QPainter(result)
        p.drawPixmap(gap, gap, pixmaps[0])
        p.drawPixmap(gap + pixmaps[0].width() + gap, gap, pixmaps[1])
        p.drawPixmap(gap, r1_h + gap * 2, pixmaps[2])
        p.drawPixmap(gap, r1_h + r2_h + gap * 3, pixmaps[3])
        p.end()
        result.save("mockup_square_strip.png")
        print("Saved mockup_square_strip.png")
        app.quit()

    QTimer.singleShot(300, capture)
    app.exec()

if __name__ == "__main__":
    main()
