import sys
import os
import logging

# Resolve app directory
if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

# Logging
LOG_FILE = os.path.join(APP_DIR, "app.log")
logging.basicConfig(
    filename=LOG_FILE, level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S", encoding="utf-8"
)
log = logging.getLogger("refbot")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor
from ui.settings_window import SettingsWindow

if __name__ == "__main__":
    log.info("App started")
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Dark palette
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(43, 43, 61))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(224, 224, 224))
    palette.setColor(QPalette.ColorRole.Base, QColor(30, 30, 48))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(43, 43, 61))
    palette.setColor(QPalette.ColorRole.Text, QColor(224, 224, 224))
    palette.setColor(QPalette.ColorRole.Button, QColor(60, 60, 80))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(224, 224, 224))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(90, 90, 180))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)

    window = SettingsWindow()
    window.show()
    sys.exit(app.exec())
