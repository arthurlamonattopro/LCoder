import importlib.util
import json
import os
import sys
from dataclasses import dataclass

from PySide6.QtWidgets import QMessageBox

from core.languages import LANGUAGES
from core.themes import THEMES


MANIFEST_FILES = ("extension.json", "package.json")
DEFAULT_ACTIVATION_EVENTS = ["onStartupFinished"]


def _safe_listdir(path):
    try:
        return os.listdir(path)
    except (FileNotFoundError, PermissionError, OSError):
        return []


def _read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _ensure_dir(path):
    os.makedirs(path, exist_ok=True)
    return path


@dataclass
class Extension:
    ext_id: str
    path: str
    manifest: dict
    activated: bool = False
    module: object = None
    deactivate_func: object = None

    @property
    def activation_events(self):
        events = self.manifest.get("activationEvents")
        if not events:
            return DEFAULT_ACTIVATION_EVENTS
        return events


class CommandRegistry:
    def __init__(self, extension_manager, log_callback):
        self._extension_manager = extension_manager
        self._log = log_callback
        self._commands = {}
        self._meta = {}

    def register_contribution(self, ext_id, command_def):
        command_id = command_def.get("id")
        if not command_id:
            return
        title = command_def.get("title") or command_id
        self._meta[command_id] = {"title": title, "extension": ext_id}

    def register_command(self, command_id, callback, title=None):
        if not command_id or not callable(callback):
            return
        self._commands[command_id] = callback
        if title:
            meta = self._meta.get(command_id, {})
            meta["title"] = title
            self._meta[command_id] = meta

    def execute_command(self, command_id, *args, **kwargs):
        callback = self._commands.get(command_id)
        if callback is None:
            meta = self._meta.get(command_id, {})
            ext_id = meta.get("extension")
            if ext_id:
                self._extension_manager.activate_extension(ext_id)
                callback = self._commands.get(command_id)

        if callback is None:
            self._log(f"[extensions] Command not found: {command_id}\n")
            return None

        try:
            return callback(*args, **kwargs)
        except Exception as exc:
            self._log(f"[extensions] Error running '{command_id}': {exc}\n")
            return None

    def get_title(self, command_id):
        meta = self._meta.get(command_id, {})
        return meta.get("title") or command_id


class LanguageRegistry:
    def __init__(self, config_manager, log_callback):
        self._config_manager = config_manager
        self._log = log_callback

    def register_language(self, language_id, config):
        if not language_id or not isinstance(config, dict):
            return

        normalized = {
            "name": config.get("name", language_id.title()),
            "extensions": config.get("extensions", []),
            "icon": config.get("icon", "FILE"),
            "executable": config.get("executable") or language_id,
            "run_args": config.get("run_args", ["{file}"]),
            "repl_args": config.get("repl_args", []),
            "keywords": config.get("keywords", []),
            "functions": config.get("functions", []),
            "comment_prefix": config.get("comment_prefix", "#"),
            "string_quotes": config.get("string_quotes", ["\"", "'"]),
            "number_pattern": config.get("number_pattern", r"\b\d+(\.\d+)?\b"),
        }

        LANGUAGES[language_id] = normalized

        if self._config_manager.get("languages", language_id) is None:
            self._config_manager.set({"path": ""}, "languages", language_id)

        self._log(f"[extensions] Language registered: {language_id}\n")


class ThemeRegistry:
    def __init__(self, log_callback):
        self._log = log_callback

    def register_theme(self, theme_id, theme, label=None):
        if not theme_id or not isinstance(theme, dict):
            return
        if label:
            theme["_label"] = label
        THEMES[theme_id] = theme
        self._log(f"[extensions] Theme registered: {theme_id}\n")


class WindowAPI:
    def __init__(self, main_window, command_registry):
        self._window = main_window
        self._commands = command_registry

    def show_info(self, message, title="LCoder"):
        QMessageBox.information(self._window, title, message)

    def show_warning(self, message, title="LCoder"):
        QMessageBox.warning(self._window, title, message)

    def show_error(self, message, title="LCoder"):
        QMessageBox.critical(self._window, title, message)

    def set_status_message(self, message, timeout_ms=None):
        if timeout_ms is None:
            self._window.statusBar().showMessage(message)
        else:
            self._window.statusBar().showMessage(message, int(timeout_ms))

    def open_file(self, path):
        self._window.abrir_arquivo_por_caminho(path)

    def active_editor(self):
        return self._window.get_current_editor()

    def add_menu_item(self, menu_name, label, command_id, shortcut=None):
        return self._window.register_command_action(menu_name, label, command_id, shortcut)


class WorkspaceAPI:
    def __init__(self, main_window):
        self._window = main_window

    def root_path(self):
        return self._window.explorer.root_path

    def open_folder(self, path):
        self._window.explorer.set_root_path(path)


class ExtensionContext:
    def __init__(self, extension_id, extension_path, storage_path, commands, window, workspace, languages, themes, log):
        self.extension_id = extension_id
        self.extension_path = extension_path
        self.global_storage_path = storage_path
        self.commands = commands
        self.window = window
        self.workspace = workspace
        self.languages = languages
        self.themes = themes
        self.log = log
        self.subscriptions = []


class ExtensionManager:
    def __init__(self, config_manager, app_root):
        self._config_manager = config_manager
        self._app_root = app_root
        self._extensions_root = os.path.join(app_root, "extensions")
        self._storage_root = os.path.join(self._extensions_root, ".storage")
        self._extensions = {}
        self._menu_contributions = []
        self._window = None
        self._log_callback = print

        self.commands = CommandRegistry(self, self._log)
        self.languages = LanguageRegistry(self._config_manager, self._log)
        self.themes = ThemeRegistry(self._log)

    def _log(self, message):
        try:
            self._log_callback(message)
        except Exception:
            print(message)

    def set_log_callback(self, callback):
        if callable(callback):
            self._log_callback = callback

    def discover_extensions(self):
        for name in _safe_listdir(self._extensions_root):
            ext_path = os.path.join(self._extensions_root, name)
            if not os.path.isdir(ext_path):
                continue

            manifest_path = None
            for candidate in MANIFEST_FILES:
                candidate_path = os.path.join(ext_path, candidate)
                if os.path.exists(candidate_path):
                    manifest_path = candidate_path
                    break

            if not manifest_path:
                continue

            try:
                manifest = _read_json(manifest_path)
            except Exception as exc:
                self._log(f"[extensions] Failed to read {manifest_path}: {exc}\n")
                continue

            name_from_manifest = manifest.get("name") or name
            publisher = manifest.get("publisher")
            ext_id = f"{publisher}.{name_from_manifest}" if publisher else name_from_manifest

            self._extensions[ext_id] = Extension(ext_id=ext_id, path=ext_path, manifest=manifest)

    def load_contributions(self):
        for extension in self._extensions.values():
            contributes = extension.manifest.get("contributes", {})

            for command_def in contributes.get("commands", []):
                if isinstance(command_def, dict):
                    self.commands.register_contribution(extension.ext_id, command_def)

            for menu_def in contributes.get("menus", []):
                if isinstance(menu_def, dict):
                    self._menu_contributions.append({"extension": extension.ext_id, **menu_def})

            for lang_def in contributes.get("languages", []):
                self._register_language_contribution(extension, lang_def)

            for theme_def in contributes.get("themes", []):
                self._register_theme_contribution(extension, theme_def)

    def _register_language_contribution(self, extension, lang_def):
        if not isinstance(lang_def, dict):
            return

        config = lang_def
        if "path" in lang_def:
            lang_path = os.path.join(extension.path, lang_def["path"])
            try:
                config = _read_json(lang_path)
            except Exception as exc:
                self._log(f"[extensions] Failed to read language file: {lang_path} ({exc})\n")
                return

        language_id = config.get("id") or lang_def.get("id")
        if not language_id:
            return
        merged = dict(config)
        for key, value in lang_def.items():
            if key in ("path", "id"):
                continue
            if key not in merged:
                merged[key] = value
        if "id" in merged:
            merged.pop("id")
        self.languages.register_language(language_id, merged)

    def _register_theme_contribution(self, extension, theme_def):
        if not isinstance(theme_def, dict):
            return

        theme = None
        theme_path = theme_def.get("path")
        if theme_path:
            path = os.path.join(extension.path, theme_path)
            try:
                theme = _read_json(path)
            except Exception as exc:
                self._log(f"[extensions] Failed to read theme file: {path} ({exc})\n")
                return

        if theme is None and "theme" in theme_def:
            theme = theme_def.get("theme")

        theme_id = theme_def.get("id") or (theme and theme.get("id"))
        if not theme_id or not isinstance(theme, dict):
            return

        label = theme_def.get("label") or theme.get("label")
        if "id" in theme:
            theme = dict(theme)
            theme.pop("id", None)
        if "label" in theme:
            theme = dict(theme)
            theme.pop("label", None)
        self.themes.register_theme(theme_id, theme, label=label)

    def attach_window(self, main_window):
        self._window = main_window
        self.set_log_callback(main_window.write_to_output)
        self._apply_menu_contributions()

    def _apply_menu_contributions(self):
        if not self._window:
            return

        for item in self._menu_contributions:
            menu_name = item.get("menu") or "Extensions"
            command_id = item.get("command")
            if not command_id:
                continue

            label = item.get("label") or self.commands.get_title(command_id)
            shortcut = item.get("shortcut")
            self._window.register_command_action(menu_name, label, command_id, shortcut)

    def activate_startup(self):
        for extension in self._extensions.values():
            events = extension.activation_events
            if "*" in events or "onStartupFinished" in events:
                self.activate_extension(extension.ext_id)

    def activate_extension(self, ext_id):
        extension = self._extensions.get(ext_id)
        if not extension:
            self._log(f"[extensions] Unknown extension: {ext_id}\n")
            return False

        if extension.activated:
            return True

        main_entry = extension.manifest.get("main") or "main.py"
        main_path = os.path.join(extension.path, main_entry)

        if not os.path.exists(main_path):
            self._log(f"[extensions] Missing entry file: {main_path}\n")
            extension.activated = True
            return True

        module_name = f"lcoder_ext_{extension.ext_id.replace('.', '_')}"
        try:
            spec = importlib.util.spec_from_file_location(module_name, main_path)
            if spec is None or spec.loader is None:
                self._log(f"[extensions] Failed to load module: {main_path}\n")
                return False
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module

            sys.path.insert(0, extension.path)
            try:
                spec.loader.exec_module(module)
            finally:
                sys.path.remove(extension.path)

            window_api = WindowAPI(self._window, self.commands) if self._window else None
            workspace_api = WorkspaceAPI(self._window) if self._window else None
            storage_path = _ensure_dir(os.path.join(self._storage_root, extension.ext_id))
            context = ExtensionContext(
                extension_id=extension.ext_id,
                extension_path=extension.path,
                storage_path=storage_path,
                commands=self.commands,
                window=window_api,
                workspace=workspace_api,
                languages=self.languages,
                themes=self.themes,
                log=self._log,
            )

            activate = getattr(module, "activate", None)
            if callable(activate):
                activate(context)

            extension.deactivate_func = getattr(module, "deactivate", None)
            extension.module = module
            extension.activated = True
            if self._window:
                try:
                    self._window._rebuild_theme_menu()
                except Exception:
                    pass
            self._log(f"[extensions] Activated: {extension.ext_id}\n")
            return True
        except Exception as exc:
            self._log(f"[extensions] Failed to activate {extension.ext_id}: {exc}\n")
            return False

    def deactivate_all(self):
        for extension in self._extensions.values():
            if extension.activated and callable(extension.deactivate_func):
                try:
                    extension.deactivate_func()
                except Exception as exc:
                    self._log(f"[extensions] Error during deactivate: {extension.ext_id} ({exc})\n")
