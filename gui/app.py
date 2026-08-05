from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from gui.main_window import MainWindow
from gui.theme import DARK_THEME


def main() -> int:
    """Create and run the Slot Model GUI application."""
    app = QApplication(sys.argv)

    app.setApplicationName("SlotModel")
    app.setOrganizationName("SlotModel")
    app.setStyle("Fusion")
    app.setStyleSheet(DARK_THEME)

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())