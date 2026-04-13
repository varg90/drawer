import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.focus_monitor import get_foreground_app, list_window_apps


def test_get_foreground_app_returns_string_or_none():
    """get_foreground_app() returns a non-empty string or None."""
    result = get_foreground_app()
    assert result is None or (isinstance(result, str) and len(result) > 0)


def test_list_window_apps_returns_list_of_strings():
    """list_window_apps() returns a list of unique app name strings."""
    result = list_window_apps()
    assert isinstance(result, list)
    for name in result:
        assert isinstance(name, str)
        assert len(name) > 0


def test_list_window_apps_no_duplicates():
    """list_window_apps() should not contain duplicate entries."""
    result = list_window_apps()
    assert len(result) == len(set(result))


def test_get_foreground_app_in_list():
    """The foreground app should appear in the running apps list."""
    fg = get_foreground_app()
    if fg is None:
        return  # headless CI
    apps = list_window_apps()
    assert fg in apps
