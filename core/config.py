import json
import os
from tkinter import messagebox

DEFAULT_CONFIG = {
    "theme": "dark",
    "current_language": "lua",
    "editor": {
        "font_family": "Consolas",
        "font_size": 12,
        "show_line_numbers": True,
        "word_wrap": False
    },
    "autocomplete": {
        "enabled": True,
        "delay": 200
    },
    "languages": {
        "lua": {"path": ""},
        "python": {"path": ""},
        "javascript": {"path": ""},
        "ruby": {"path": ""},
        "php": {"path": ""},
        "perl": {"path": ""},
        "cpp": {"path": ""},
        "html": {"path": ""}
    },
    "window": {
        "width": 1400,
        "height": 900,
        "maximized": False
    }
}

class ConfigManager:
    def __init__(self, config_file="ide_config.json"):
        self.config_file = config_file
        self.current_config = DEFAULT_CONFIG.copy()
        self.load()

    def load(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    self._merge_config(self.current_config, loaded_config)
        except Exception as e:
            print(f"Erro ao carregar configurações: {e}")

    def _merge_config(self, default, loaded):
        for key, value in loaded.items():
            if key in default:
                if isinstance(value, dict) and isinstance(default[key], dict):
                    self._merge_config(default[key], value)
                else:
                    default[key] = value

    def save(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.current_config, f, indent=4)
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar configurações: {e}")

    def get(self, *keys):
        val = self.current_config
        for key in keys:
            if isinstance(val, dict) and key in val:
                val = val[key]
            else:
                return None
        return val

    def set(self, value, *keys):
        val = self.current_config
        for key in keys[:-1]:
            if key not in val:
                val[key] = {}
            val = val[key]
        val[keys[-1]] = value
