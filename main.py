import sys
import os
import logging

if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

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


def load_fonts() -> None:
    """Register custom fonts with Qt. Logs a warning if any file is missing."""
    font_files = [
        os.path.join(APP_DIR, "fonts", "Lora-Bold.ttf"),
        os.path.join(APP_DIR, "fonts", "Lexend[wght].ttf"),
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
    load_fonts()
    app.setFont(QFont("Lexend"))
    window = SettingsWindow()
    window.show()
    sys.exit(app.exec())
