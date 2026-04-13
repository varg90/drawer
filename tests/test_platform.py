import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ui.platform import setup_frameless_native


def test_setup_frameless_native_noop_on_non_darwin():
    """On non-macOS platforms, setup_frameless_native returns False."""
    if sys.platform == "darwin":
        return  # skip on macOS — would actually run native code
    assert setup_frameless_native(None) == False
