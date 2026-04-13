import sys
import os
import logging
import platform

# Tell Windows this is a separate app (shows our icon in taskbar, not Python's)
if platform.system() == "Windows":
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("drawer.app")

if getattr(sys, "frozen", False):
    DATA_DIR = sys._MEIPASS
    APP_DIR = os.path.dirname(sys.executable)
else:
    DATA_DIR = os.path.dirname(os.path.abspath(__file__))
    APP_DIR = DATA_DIR

LOG_FILE = os.path.join(APP_DIR, "app.log")
logging.basicConfig(
    filename=LOG_FILE, level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S", encoding="utf-8"
)
log = logging.getLogger("refbot")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont, QFontDatabase
from ui.settings_window import SettingsWindow
from ui.scales import init_scale


REFERENCE_HEIGHT = 1080
MAX_SCALE = 2.0


def detect_scale_factor(screen_height):
    """Compute UI scale factor from screen logical height."""
    return min(max(1.0, round(screen_height / REFERENCE_HEIGHT, 2)), MAX_SCALE)


def load_fonts() -> None:
    """Register custom fonts with Qt. Logs a warning if any file is missing."""
    font_files = [
        os.path.join(DATA_DIR, "fonts", "Lora[wght].ttf"),
        os.path.join(DATA_DIR, "fonts", "Lexend[wght].ttf"),
    ]
    for path in font_files:
        if not os.path.isfile(path):
            log.warning("Font file not found, skipping: %s", path)
            continue
        font_id = QFontDatabase.addApplicationFont(path)
        if font_id == -1:
            log.warning("Qt could not load font: %s", path)
        else:
            families = QFontDatabase.applicationFontFamilies(font_id)
            log.info("Loaded font %s → families: %s", os.path.basename(path), families)


if __name__ == "__main__":
    log.info("App started")
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Detect scale factor from primary screen
    screen = app.primaryScreen()
    if screen:
        height = screen.availableSize().height()
        factor = detect_scale_factor(height)
        log.info("Screen height: %d, scale factor: %.2f", height, factor)
    else:
        factor = 1.0
        log.warning("No screen detected, using factor 1.0")
    init_scale(factor, user_factor=1.0)

    load_fonts()
    app.setFont(QFont("Lexend"))
    window = SettingsWindow()
    window.show()
    sys.exit(app.exec())
