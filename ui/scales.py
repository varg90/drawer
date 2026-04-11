# ui/scales.py
"""Centralized size definitions — single source of truth for all UI dimensions."""


class S:
    # Window
    MAIN_W = 250
    MAIN_H = 250
    EDITOR_W = 250
    WINDOW_RADIUS = 8

    # Margins
    MARGIN = 14
    MARGIN_TOP = 12
    MARGIN_BOTTOM = 14

    # Icons — header row
    ICON_HEADER = 13
    ACCENT_DOT = 11

    # Icons — bottom bar
    ICON_START = 52

    # Start button
    START_ICON_RATIO = 0.75
    START_RADIUS_RATIO = 0.19  # ~10px on 52px button

    # Title
    TITLE_W = 105

    # Fonts (px)
    FONT_TITLE = 17
    FONT_BUTTON = 11
    FONT_MODE = 11
    FONT_LABEL = 9
    FONT_HINT = 10
    FONT_TOTAL = 13

    # Spacing
    SPACING_HEADER = 6
    SPACING_MODE = 6
    SPACING_TIERS = 4
    SPACING_SUMMARY = 6

    # Timer buttons
    TIMER_BTN_PADDING_V = 7
    TIMER_BTN_PADDING_H = 7
    TIMER_BTN_RADIUS = 5
    MODE_BTN_RADIUS = 5
    PANEL_RADIUS = 6
    PANEL_PADDING = 6

    # Editor toolbar buttons
    EDITOR_BTN = 15
