# ui/scales.py
"""Centralized size definitions — single source of truth for all UI dimensions."""

_factor = 1.0
_dpi_factor = 1.0
_user_factor = 1.0

# Base values (unscaled) — used by init_scale to recompute S.* constants
_BASE = {}


def sc(value):
    """Scale a pixel value by the current factor, rounded to int."""
    return round(value * _factor)


def init_scale(dpi_factor, user_factor=1.0):
    """Set DPI and user scale factors. Recomputes all S.* constants."""
    global _factor, _dpi_factor, _user_factor
    _dpi_factor = dpi_factor
    _user_factor = user_factor
    _factor = dpi_factor * user_factor
    for attr, val in _BASE.items():
        setattr(S, attr, round(val * _factor))


def rescale_user(user_factor):
    """Change user scale factor only, keeping DPI factor."""
    init_scale(_dpi_factor, user_factor)


class _SMeta(type):
    """Metaclass that records base values of int class attributes."""
    def __init__(cls, name, bases, namespace):
        super().__init__(name, bases, namespace)
        for attr, val in namespace.items():
            if attr.startswith('_'):
                continue
            if isinstance(val, int):
                _BASE[attr] = val
            # floats (ratios) are NOT recorded — they don't scale


class S(metaclass=_SMeta):
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

    # Start button (ratios — NOT scaled)
    START_ICON_RATIO = 0.75
    START_RADIUS_RATIO = 0.19  # ~10px on 52px button

    # Title
    TITLE_W = 105
    TITLE_Y_NUDGE = 4

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

    # Editor
    EDITOR_BTN = 15
    EDITOR_BTN_BOTTOM = 11

    # Viewer window
    VIEWER_MIN_W = 230
    VIEWER_MIN_H = 150
    VIEWER_CORNER_GRIP = 50
    VIEWER_NAV_ZONE = 40
    VIEWER_CENTER_BTN = 60
    VIEWER_ICON_LABEL = 20
    VIEWER_ICON_BTN = 26
    VIEWER_ICON_MARGIN = 8
    VIEWER_ICON_GAP = 4
    VIEWER_PROGRESS_H = 3
    VIEWER_BOTTOM_LABEL_H = 24
    VIEWER_BOTTOM_OFFSET = 8
    VIEWER_BOTTOM_LABEL_X = 10
    VIEWER_BOTTOM_ICON_SPACING = 26
    VIEWER_BOTTOM_ICON_Y_OFFSET = 2
    VIEWER_LEFT_NAV_X = 4
    VIEWER_LEFT_NAV_W = 25
    VIEWER_LEFT_NAV_H = 40
    VIEWER_HELP_MARGIN = 20

    # Viewer fonts (px)
    FONT_TIMER = 20
    FONT_COUNTER = 13
    FONT_HELP = 14

    # Scrollbar
    SCROLLBAR_W = 4
    SCROLLBAR_HANDLE_MIN_H = 20
    SCROLLBAR_RADIUS = 2

    # Editor panel
    GRID_MIN = 48
    GRID_MAX = 256
    GRID_DEFAULT = 80
    GRID_ZOOM_STEP = 16
    GRID_TILE_RADIUS = 3
    GRID_SPACING = 4
    COLOR_LINE_H = 1
    ZOOM_SLIDER_W = 90
    LIST_ITEM_H = 30
    LIST_ITEM_PADDING = 2
    LIST_PADDING = 4
    LIST_SPACING = 4
    HEADER_PADDING_TOP = 3
    HEADER_PADDING_H = 2
    HEADER_PADDING_BOTTOM = 1
    SLIDER_GROOVE_H = 4
    SLIDER_HANDLE_W = 12
    SLIDER_HANDLE_MARGIN = 4
    PIN_OVERLAY_PADDING = 2
    PIN_POS_X_OFFSET = 4
    PIN_POS_Y_OFFSET = 2
    FONT_MSG_BOX = 12
    EDITOR_BORDER_SELECTED = 2
    EDITOR_BORDER_DASHED = 1

    # Accent picker
    ACCENT_SQ = 120
    ACCENT_BAR_W = 12
    ACCENT_MARGIN = 10
    ACCENT_SPACING = 8
    ACCENT_ROW_SPACING = 6
    ACCENT_HEX_H = 20
    ACCENT_HEX_RADIUS = 2
    ACCENT_HEX_FONT = 10
    ACCENT_OFFSET_Y = 4

    # Timer panel
    TIMER_MODE_BTN_H = 28
    MODE_BTN_PADDING_V = 4
    MODE_BTN_PADDING_H = 8

    # Image editor window
    RESIZE_GRIP_W = 6
    RESIZE_CURSOR_W = 14
    EDITOR_TITLE_SPACING = 4
    EDITOR_TITLE_BOTTOM_SPACE = 6
    EDITOR_MIN_W = 200
    EDITOR_MIN_H = 200
    EDGE_SNAP_THRESHOLD = 12

    # Snap
    SNAP_DISTANCE = 15
    DETACH_DISTANCE = 40

    # Bottom bar
    SUMMARY_TIME_SPACING = 4
    START_BTN_SPACING = 8
    FONT_LIMIT_BTN = 9
    FONT_LIMIT_SEP = 10

    # URL dialog
    URL_DLG_MIN_W = 400
    URL_DLG_MARGIN_H = 16
    URL_DLG_MARGIN_V = 12
    URL_DLG_SPACING = 8
    URL_ROW_SPACING = 6
    URL_FILE_LIST_MIN_H = 200
    URL_PREVIEW_SIZE = 48
    URL_INPUT_PADDING = 6
    URL_INPUT_FONT = 11
    URL_BTN_FONT = 10
    URL_BTN_PADDING_V = 3
    URL_BTN_PADDING_H = 6
    URL_LIST_ITEM_PADDING = 3
    URL_PROGRESS_H = 8

    # Widgets / misc
    BORDER_WIDTH = 1


# Constants that must NOT scale (rendering details, not layout dimensions)
TEXT_SHADOW_OFFSET = 1
