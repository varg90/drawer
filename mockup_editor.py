"""Editor panel: collapsible groups, list + grid view, reserve section."""
import sys
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                              QLabel, QPushButton, QFrame, QScrollArea)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QPixmap, QPainter, QColor
import qtawesome as qta

DARK = {
    "bg": "#191919", "bg2": "#171717", "btn": "#222222",
    "active": "#333b3a", "border": "#303030", "accent": "#4a7d74",
    "primary": "#ddd", "secondary": "#606060", "hint": "#454545",
    "header": "#84a39e", "btn_text": "#84a39e", "start_text": "#252525",
    "warning": "#cc5555",
}


def _group_header(t, label, count, collapsed=False, inactive=False):
    btn = QPushButton(f"  {label} — {count}")
    btn.setStyleSheet(
        f"background-color: {t['btn']}; "
        f"color: {t['hint'] if inactive else t['secondary']}; "
        f"border: 1px solid {t['border']}; font-size: 10px; font-weight: 500; "
        f"padding: 3px 8px; text-align: left;")
    btn.setFixedHeight(22)
    return btn


def _file_row(t, idx, name, timer, pinned=False):
    row = QHBoxLayout()
    row.setContentsMargins(6, 1, 6, 1)
    row.setSpacing(4)

    num = QLabel(f"{idx}.")
    num.setFixedWidth(18)
    num.setStyleSheet(f"color: {t['hint']}; font-size: 10px;")
    row.addWidget(num)

    if pinned:
        pin = QLabel()
        pin.setPixmap(qta.icon("ph.push-pin-fill", color=t["accent"]).pixmap(QSize(10, 10)))
        pin.setFixedSize(10, 10)
        pin.setStyleSheet("background: transparent;")
        row.addWidget(pin)

    fname = QLabel(name)
    fname.setStyleSheet(
        f"color: {t['accent'] if pinned else t['primary']}; font-size: 10px;")
    row.addWidget(fname, 1)

    time_lbl = QLabel(timer)
    time_lbl.setStyleSheet(f"color: {t['secondary']}; font-size: 10px;")
    row.addWidget(time_lbl)

    return row


def _file_row_reserve(t, idx, name):
    row = QHBoxLayout()
    row.setContentsMargins(6, 1, 6, 1)
    row.setSpacing(4)

    num = QLabel(f"{idx}.")
    num.setFixedWidth(18)
    num.setStyleSheet(f"color: {t['hint']}; font-size: 10px;")
    row.addWidget(num)

    fname = QLabel(name)
    fname.setStyleSheet(f"color: {t['hint']}; font-size: 10px;")
    row.addWidget(fname, 1)

    dash = QLabel("—")
    dash.setStyleSheet(f"color: {t['hint']}; font-size: 10px;")
    row.addWidget(dash)

    return row


def _tile(t, name, timer=None, pinned=False):
    lbl = QLabel()
    lbl.setFixedSize(52, 52)
    if timer:
        bg = t['bg2']
    else:
        bg = t['btn']
    border = f"2px solid {t['accent']}" if pinned else f"1px solid {t['border']}"
    lbl.setStyleSheet(f"background-color: {bg}; border: {border};")
    return lbl


def _build_list_view(t, over_budget=False):
    """List view with collapsible groups."""
    w = QWidget()
    w.setFixedSize(300, 480)
    w.setStyleSheet(f"background-color: {t['bg']};")
    root = QVBoxLayout(w)
    root.setContentsMargins(10, 10, 10, 12)
    root.setSpacing(4)

    tag = QLabel("List view" + (" — over budget" if over_budget else ""))
    tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
    tag.setStyleSheet(f"color: {t['hint']}; font-size: 8px;")
    root.addWidget(tag)

    # Toolbar
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
    root.addLayout(tb)

    cnt = QLabel("IMAGES — 11")
    cnt.setStyleSheet(f"color: {t['secondary']}; font-size: 9px; font-weight: 500; letter-spacing: 1px;")
    root.addWidget(cnt)

    # Scrollable file list area with dashed border (drop target)
    list_area = QWidget()
    list_area.setStyleSheet(
        f"background-color: {t['bg2']}; border: 1px dashed {t['border']};")
    la_layout = QVBoxLayout(list_area)
    la_layout.setContentsMargins(2, 2, 2, 2)
    la_layout.setSpacing(2)

    # Group: 1m — 2
    la_layout.addWidget(_group_header(t, "1m", 2))
    la_layout.addLayout(_file_row(t, 1, "portrait_001.jpg", "1:00"))
    la_layout.addLayout(_file_row(t, 2, "portrait_002.jpg", "1:00", pinned=True))

    # Group: 5m — 3
    la_layout.addWidget(_group_header(t, "5m", 3))
    la_layout.addLayout(_file_row(t, 3, "gesture_001.jpg", "5:00"))
    la_layout.addLayout(_file_row(t, 4, "gesture_002.jpg", "5:00"))
    la_layout.addLayout(_file_row(t, 5, "gesture_003.jpg", "5:00", pinned=True))

    # Group: 10m — 2
    la_layout.addWidget(_group_header(t, "10m", 2))
    la_layout.addLayout(_file_row(t, 6, "anatomy_001.jpg", "10:00"))
    la_layout.addLayout(_file_row(t, 7, "anatomy_002.jpg", "10:00"))

    if over_budget:
        # Group: Reserve — 4 (new files added, over budget)
        la_layout.addWidget(_group_header(t, "Reserve", 4, inactive=True))
        la_layout.addLayout(_file_row_reserve(t, 8, "extra_001.jpg"))
        la_layout.addLayout(_file_row_reserve(t, 9, "extra_002.jpg"))
        la_layout.addLayout(_file_row_reserve(t, 10, "extra_003.jpg"))
        la_layout.addLayout(_file_row_reserve(t, 11, "extra_004.jpg"))
    else:
        # Group: 15m — 1 (collapsed)
        la_layout.addWidget(_group_header(t, "15m", 1, collapsed=True))

    la_layout.addStretch()
    root.addWidget(list_area, 1)

    # Bottom: view toggles + distribution
    bot = QHBoxLayout()
    bot.setSpacing(4)
    for i, icon_name in enumerate(["ph.list-bullets-bold", "ph.squares-four-bold"]):
        b = QPushButton()
        b.setIcon(qta.icon(icon_name, color=t["primary"] if i == 0 else t["btn_text"]))
        b.setIconSize(QSize(12, 12))
        b.setFixedSize(20, 20)
        active_s = f"background-color: {t['active']}; border: 1px solid {t['accent']};"
        inactive_s = f"background-color: {t['btn']}; border: 1px solid {t['border']};"
        b.setStyleSheet(active_s if i == 0 else inactive_s)
        bot.addWidget(b)
    bot.addStretch()
    dist = QLabel("2x1m 3x5m 2x10m 1x15m")
    dist.setStyleSheet(f"color: {t['secondary']}; font-size: 9px;")
    bot.addWidget(dist)
    root.addLayout(bot)

    # Total
    if over_budget:
        total = QLabel("1:07:00 / 1:00:00")
        total.setStyleSheet(f"color: {t['warning']}; font-size: 10px;")
    else:
        total = QLabel("0:37:00")
        total.setStyleSheet(f"color: {t['primary']}; font-size: 10px;")
    root.addWidget(total)

    return w


def _build_grid_view(t, over_budget=False):
    """Grid/tile view with collapsible groups."""
    w = QWidget()
    w.setFixedSize(300, 480)
    w.setStyleSheet(f"background-color: {t['bg']};")
    root = QVBoxLayout(w)
    root.setContentsMargins(10, 10, 10, 12)
    root.setSpacing(4)

    tag = QLabel("Grid view" + (" — over budget" if over_budget else ""))
    tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
    tag.setStyleSheet(f"color: {t['hint']}; font-size: 8px;")
    root.addWidget(tag)

    # Toolbar
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
    root.addLayout(tb)

    cnt = QLabel("IMAGES — 11")
    cnt.setStyleSheet(f"color: {t['secondary']}; font-size: 9px; font-weight: 500; letter-spacing: 1px;")
    root.addWidget(cnt)

    # Grid area with dashed border (drop target)
    grid_area = QWidget()
    grid_area.setStyleSheet(
        f"background-color: {t['bg2']}; border: 1px dashed {t['border']};")
    ga_layout = QVBoxLayout(grid_area)
    ga_layout.setContentsMargins(4, 4, 4, 4)
    ga_layout.setSpacing(4)

    # Group: 1m — 2
    ga_layout.addWidget(_group_header(t, "1m", 2))
    row1 = QHBoxLayout()
    row1.setSpacing(3)
    row1.addWidget(_tile(t, "portrait_001", "1m"))
    row1.addWidget(_tile(t, "portrait_002", "1m", pinned=True))
    row1.addStretch()
    ga_layout.addLayout(row1)

    # Group: 5m — 3
    ga_layout.addWidget(_group_header(t, "5m", 3))
    row2 = QHBoxLayout()
    row2.setSpacing(3)
    row2.addWidget(_tile(t, "gesture_001", "5m"))
    row2.addWidget(_tile(t, "gesture_002", "5m"))
    row2.addWidget(_tile(t, "gesture_003", "5m", pinned=True))
    row2.addStretch()
    ga_layout.addLayout(row2)

    # Group: 10m — 2
    ga_layout.addWidget(_group_header(t, "10m", 2))
    row3 = QHBoxLayout()
    row3.setSpacing(3)
    row3.addWidget(_tile(t, "anatomy_001", "10m"))
    row3.addWidget(_tile(t, "anatomy_002", "10m"))
    row3.addStretch()
    ga_layout.addLayout(row3)

    if over_budget:
        # Reserve group
        ga_layout.addWidget(_group_header(t, "Reserve", 4, inactive=True))
        row4 = QHBoxLayout()
        row4.setSpacing(3)
        for _ in range(4):
            tile = _tile(t, "extra", None)
            tile.setStyleSheet(
                f"background-color: {t['btn']}; border: 1px dashed {t['hint']};")
            row4.addWidget(tile)
        row4.addStretch()
        ga_layout.addLayout(row4)
    else:
        # 15m — 1 (collapsed)
        ga_layout.addWidget(_group_header(t, "15m", 1, collapsed=True))

    ga_layout.addStretch()
    root.addWidget(grid_area, 1)

    # Bottom
    bot = QHBoxLayout()
    bot.setSpacing(4)
    for i, icon_name in enumerate(["ph.list-bullets-bold", "ph.squares-four-bold"]):
        b = QPushButton()
        b.setIcon(qta.icon(icon_name, color=t["primary"] if i == 1 else t["btn_text"]))
        b.setIconSize(QSize(12, 12))
        b.setFixedSize(20, 20)
        active_s = f"background-color: {t['active']}; border: 1px solid {t['accent']};"
        inactive_s = f"background-color: {t['btn']}; border: 1px solid {t['border']};"
        b.setStyleSheet(active_s if i == 1 else inactive_s)
        bot.addWidget(b)
    bot.addStretch()
    dist = QLabel("2x1m 3x5m 2x10m 1x15m")
    dist.setStyleSheet(f"color: {t['secondary']}; font-size: 9px;")
    bot.addWidget(dist)
    root.addLayout(bot)

    if over_budget:
        total = QLabel("1:07:00 / 1:00:00")
        total.setStyleSheet(f"color: {t['warning']}; font-size: 10px;")
    else:
        total = QLabel("0:37:00")
        total.setStyleSheet(f"color: {t['primary']}; font-size: 10px;")
    root.addWidget(total)

    return w


def main():
    app = QApplication(sys.argv)
    t = DARK

    widgets = [
        _build_list_view(t, over_budget=False),
        _build_list_view(t, over_budget=True),
        _build_grid_view(t, over_budget=False),
        _build_grid_view(t, over_budget=True),
    ]
    for w in widgets:
        w.show()

    def capture():
        pixmaps = [w.grab() for w in widgets]
        gap = 10

        r1_w = pixmaps[0].width() + pixmaps[1].width() + gap * 3
        r1_h = max(pixmaps[0].height(), pixmaps[1].height())
        r2_w = pixmaps[2].width() + pixmaps[3].width() + gap * 3
        r2_h = max(pixmaps[2].height(), pixmaps[3].height())

        total_w = max(r1_w, r2_w)
        total_h = r1_h + r2_h + gap * 3

        result = QPixmap(total_w, total_h)
        result.fill(QColor("#111"))
        p = QPainter(result)
        p.drawPixmap(gap, gap, pixmaps[0])
        p.drawPixmap(gap + pixmaps[0].width() + gap, gap, pixmaps[1])
        p.drawPixmap(gap, r1_h + gap * 2, pixmaps[2])
        p.drawPixmap(gap + pixmaps[2].width() + gap, r1_h + gap * 2, pixmaps[3])
        p.end()
        result.save("mockup_editor.png")
        print("Saved mockup_editor.png")
        app.quit()

    QTimer.singleShot(300, capture)
    app.exec()

if __name__ == "__main__":
    main()
