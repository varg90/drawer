import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_import():
    import main
    assert hasattr(main, "SUPPORTED_FORMATS")
