# ui/scales.py
"""Centralized size definitions — single source of truth for all UI dimensions."""


class S:
    # Window
    MAIN_W = 250
    MAIN_H = 270
    EDITOR_W = 250

    # Margins
    MARGIN = 14
    MARGIN_BOTTOM = 18

    # Icons — header row
    ICON_HEADER = 13
    ACCENT_DOT = 11

    # Icons — bottom bar
    ICON_DICE = 34
    ICON_START = 42

    # Start button
    START_ICON_RATIO = 0.75
    START_RADIUS_RATIO = 0.12

    # Fonts (px)
    FONT_TITLE = 11
    FONT_BUTTON = 10
    FONT_LABEL = 9
    FONT_HINT = 8
    FONT_DURATION = 18
    FONT_TOTAL = 10

    # Spacing
    SPACING_HEADER = 6
    SPACING_MODE = 10
    SPACING_DURATION = 12
    SPACING_TIERS = 3
    SPACING_SUMMARY = 6

    # Duration picker
    DURATION_ARROW = 14
    DURATION_ARROW_BTN = 22

    # Timer buttons
    TIMER_BTN_PADDING_V = 4
    TIMER_BTN_PADDING_H = 7

    # Editor toolbar buttons
    EDITOR_BTN = 20
    EDITOR_BTN_ICON = 11
