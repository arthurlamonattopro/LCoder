from core.config import ConfigManager
from ui.main_window import MainWindow

def main():
    config_manager = ConfigManager()
    app = MainWindow(config_manager)
    
    try:
        app.mainloop()
    finally:
        config_manager.save()

if __name__ == "__main__":
    main()
