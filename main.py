import sys

from PySide6.QtWidgets import QApplication

from core.config import ConfigManager
from ui.main_window import MainWindow


def main():
    config_manager = ConfigManager()
    app = QApplication(sys.argv)
    window = MainWindow(config_manager)
    window.show()

    exit_code = 0
    try:
        exit_code = app.exec()
    finally:
        config_manager.save()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
