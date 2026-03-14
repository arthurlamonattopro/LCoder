import json
import os

from PySide6.QtCore import QEvent, QRegularExpression, Signal, Qt
from PySide6.QtGui import QAction, QTextCursor, QTextDocument
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.extensions import ExtensionManager
from core.languages import LANGUAGES, detectar_linguagem_por_extensao
from core.themes import THEMES
from ui.editor import Editor
from ui.explorer import Explorer
from utils.process_mgr import ProcessManager


class MainWindow(QMainWindow):
    output_received = Signal(str)

    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager
        self.open_file_tabs = {}
        self.tab_meta = {}
        self.untitled_count = 1
        self.closed_tabs = []
        self._terminal_history = []
        self._terminal_history_index = -1
        self.process_manager = ProcessManager(self.write_to_output)

        self.app_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.extension_manager = ExtensionManager(self.config_manager, self.app_root)
        self.extension_manager.discover_extensions()
        self.extension_manager.load_contributions()

        self.setWindowTitle("LCoder IDE")
        self.resize(
            self.config_manager.get("window", "width") or 1400,
            self.config_manager.get("window", "height") or 900,
        )

        self.output_received.connect(self._safe_write_to_output)

        self.setup_ui()
        self.setup_menus()
        self._restore_session()
        self.extension_manager.attach_window(self)
        self.aplicar_tema()
        self.extension_manager.activate_startup()
        self.atualizar_titulo()

    def setup_ui(self):
        splitter = QSplitter()
        self.setCentralWidget(splitter)

        sidebar = QWidget()
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(10, 10, 10, 10)

        self.sidebar_label = QLabel("EXPLORER")
        sidebar_layout.addWidget(self.sidebar_label)

        self.explorer_filter = QLineEdit()
        self.explorer_filter.setPlaceholderText("Filter files...")
        sidebar_layout.addWidget(self.explorer_filter)

        self.explorer = Explorer(self.config_manager, open_file_callback=self.abrir_arquivo_por_caminho)
        sidebar_layout.addWidget(self.explorer)
        self.explorer_filter.textChanged.connect(self.explorer.set_filter)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(6, 6, 6, 6)

        self.main_tabs = QTabWidget()
        content_layout.addWidget(self.main_tabs)

        self.tab_editors = QWidget()
        self.tab_output = QWidget()
        self.tab_terminal = QWidget()

        self.main_tabs.addTab(self.tab_editors, "Editors")
        self.main_tabs.addTab(self.tab_output, "Output")
        self.main_tabs.addTab(self.tab_terminal, "Terminal")

        self._setup_editors_tab()
        self._setup_output_tab()
        self._setup_terminal_tab()

        splitter.addWidget(sidebar)
        splitter.addWidget(content)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([280, 1120])

        self.statusBar().showMessage("Ready")

    def _setup_editors_tab(self):
        layout = QVBoxLayout(self.tab_editors)
        layout.setContentsMargins(0, 0, 0, 0)

        self.editor_tabs = QTabWidget()
        self.editor_tabs.setTabsClosable(True)
        self.editor_tabs.currentChanged.connect(lambda _: self._on_editor_tab_changed())
        self.editor_tabs.tabCloseRequested.connect(self._close_tab_by_index)
        layout.addWidget(self.editor_tabs)

    def _setup_output_tab(self):
        layout = QVBoxLayout(self.tab_output)
        layout.setContentsMargins(0, 0, 0, 0)
        self.output_box = QTextEdit()
        self.output_box.setReadOnly(True)
        layout.addWidget(self.output_box)

    def _setup_terminal_tab(self):
        layout = QVBoxLayout(self.tab_terminal)
        layout.setContentsMargins(0, 0, 0, 0)

        input_row = QHBoxLayout()
        self.term_entry = QLineEdit()
        self.term_entry.setPlaceholderText("Enter command...")
        self.term_entry.returnPressed.connect(self.send_terminal_command)
        self.term_entry.installEventFilter(self)
        input_row.addWidget(self.term_entry)

        self.btn_send = QPushButton("Send")
        self.btn_send.clicked.connect(self.send_terminal_command)
        input_row.addWidget(self.btn_send)

        layout.addLayout(input_row)

        self.term_output = QTextEdit()
        self.term_output.setReadOnly(True)
        layout.addWidget(self.term_output)

    def setup_menus(self):
        menubar = self.menuBar()
        self.menus = {}

        file_menu = menubar.addMenu("File")
        self.menus["File"] = file_menu
        file_menu.addAction(self._make_action("New File", "Ctrl+N", self.novo_arquivo))
        file_menu.addAction(self._make_action("Open File", "Ctrl+O", self.abrir_arquivo))
        file_menu.addAction(self._make_action("Save", "Ctrl+S", self.salvar_arquivo))
        file_menu.addAction(self._make_action("Close Tab", "Ctrl+W", self.fechar_aba_atual))
        file_menu.addSeparator()
        file_menu.addAction(self._make_action("Open Folder", None, self.abrir_pasta))
        self.recent_menu = QMenu("Open Recent", self)
        file_menu.addMenu(self.recent_menu)
        self._rebuild_recent_menu()
        file_menu.addSeparator()
        file_menu.addAction(self._make_action("Exit", None, self.close))

        edit_menu = menubar.addMenu("Edit")
        self.menus["Edit"] = edit_menu
        edit_menu.addAction(self._make_action("Find", "Ctrl+F", self.show_find_dialog))
        edit_menu.addAction(self._make_action("Go to Line", "Ctrl+G", self.show_goto_line_dialog))
        edit_menu.addAction(self._make_action("Reopen Closed Tab", "Ctrl+Shift+T", self.reopen_closed_tab))

        self.theme_menu = menubar.addMenu("Theme")
        self.menus["Theme"] = self.theme_menu
        self._rebuild_theme_menu()

        extensions_menu = menubar.addMenu("Extensions")
        self.menus["Extensions"] = extensions_menu

    def _restore_session(self):
        workspace = self.config_manager.get("workspace") or {}
        root_path = workspace.get("root_path") or ""
        if root_path and os.path.isdir(root_path):
            self.explorer.set_root_path(root_path)
            self._add_recent_folder(root_path)
        data = self._load_workspace_file(root_path) if root_path else {}
        if data:
            self._apply_workspace_data(data)
            return

        open_files = workspace.get("open_files") or []
        for path in open_files:
            if path and os.path.isfile(path):
                self.abrir_arquivo_por_caminho(path)

        active_file = workspace.get("active_file")
        if active_file and active_file in self.open_file_tabs:
            self.editor_tabs.setCurrentWidget(self.open_file_tabs[active_file])

        self._terminal_history = workspace.get("terminal_history") or []
        self._terminal_history_index = len(self._terminal_history)

    def _save_session(self):
        open_files = [meta.get("path") for meta in self.tab_meta.values() if meta.get("path")]
        active_meta = self.get_current_tab_meta()
        active_file = active_meta.get("path") if active_meta else ""
        self.config_manager.set(self.explorer.root_path or "", "workspace", "root_path")
        self.config_manager.set(open_files, "workspace", "open_files")
        self.config_manager.set(active_file or "", "workspace", "active_file")
        self.config_manager.set(self._terminal_history, "workspace", "terminal_history")

        root_path = self.explorer.root_path
        if root_path:
            self._save_workspace_file(root_path, open_files, active_file, self._terminal_history)

    def _workspace_file_path(self, root_path):
        return os.path.join(root_path, ".lcoder", "workspace.json")

    def _load_workspace_file(self, root_path):
        path = self._workspace_file_path(root_path)
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _save_workspace_file(self, root_path, open_files, active_file, terminal_history):
        try:
            folder = os.path.join(root_path, ".lcoder")
            os.makedirs(folder, exist_ok=True)
            path = self._workspace_file_path(root_path)
            data = {
                "open_files": open_files,
                "active_file": active_file or "",
                "terminal_history": terminal_history,
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def _apply_workspace_data(self, data):
        open_files = data.get("open_files") or []
        for path in open_files:
            if path and os.path.isfile(path):
                self.abrir_arquivo_por_caminho(path)

        active_file = data.get("active_file")
        if active_file and active_file in self.open_file_tabs:
            self.editor_tabs.setCurrentWidget(self.open_file_tabs[active_file])

        self._terminal_history = data.get("terminal_history") or []
        self._terminal_history_index = len(self._terminal_history)

    def _rebuild_recent_menu(self):
        if not hasattr(self, "recent_menu") or self.recent_menu is None:
            return
        self.recent_menu.clear()
        recent = self.config_manager.get("recent_folders") or []
        if not recent:
            action = QAction("No recent folders", self)
            action.setEnabled(False)
            self.recent_menu.addAction(action)
            return

        for path in recent:
            action = QAction(path, self)
            action.triggered.connect(lambda checked=False, p=path: self._open_recent_folder(p))
            self.recent_menu.addAction(action)

        self.recent_menu.addSeparator()
        clear_action = QAction("Clear Recent", self)
        clear_action.triggered.connect(self._clear_recent_folders)
        self.recent_menu.addAction(clear_action)

    def _add_recent_folder(self, path):
        if not path:
            return
        recent = self.config_manager.get("recent_folders") or []
        if path in recent:
            recent.remove(path)
        recent.insert(0, path)
        recent = recent[:10]
        self.config_manager.set(recent, "recent_folders")
        self._rebuild_recent_menu()

    def _clear_recent_folders(self):
        self.config_manager.set([], "recent_folders")
        self._rebuild_recent_menu()

    def _open_recent_folder(self, path):
        if path and os.path.isdir(path):
            self._close_all_tabs()
            self.explorer.set_root_path(path)
            self._add_recent_folder(path)
            data = self._load_workspace_file(path)
            if data:
                self._apply_workspace_data(data)

    def _make_action(self, label, shortcut, callback):
        action = QAction(label, self)
        if shortcut:
            action.setShortcut(shortcut)
        action.triggered.connect(callback)
        return action

    def register_command_action(self, menu_name, label, command_id, shortcut=None):
        menu = self.menus.get(menu_name)
        if menu is None:
            menu = self.menuBar().addMenu(menu_name)
            self.menus[menu_name] = menu

        action = QAction(label, self)
        if shortcut:
            action.setShortcut(shortcut)
        action.triggered.connect(lambda checked=False: self.extension_manager.commands.execute_command(command_id))
        menu.addAction(action)
        return action

    def _rebuild_theme_menu(self):
        self.theme_menu.clear()
        for theme_name, theme in THEMES.items():
            label = theme.get("_label") if isinstance(theme, dict) else None
            title = label or theme_name.title()
            self.theme_menu.addAction(
                self._make_action(title, None, lambda checked=False, t=theme_name: self.mudar_tema(t))
            )
        self.theme_menu.addSeparator()
        self.theme_menu.addAction(self._make_action("Theme Editor", None, self.show_theme_editor))

    def _on_editor_tab_changed(self):
        self.atualizar_titulo()
        self.atualizar_status()

    def get_current_tab_meta(self):
        widget = self.editor_tabs.currentWidget()
        if widget is None:
            return None
        return self.tab_meta.get(widget)

    def get_current_editor(self):
        meta = self.get_current_tab_meta()
        if not meta:
            return None
        return meta["editor"]

    def novo_arquivo(self):
        name = f"Untitled-{self.untitled_count}"
        self.untitled_count += 1
        self.criar_aba_editor(None, "", name)

    def abrir_arquivo(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open File")
        if path:
            self.abrir_arquivo_por_caminho(path)

    def abrir_arquivo_por_caminho(self, path):
        if path in self.open_file_tabs:
            self.editor_tabs.setCurrentWidget(self.open_file_tabs[path])
            return

        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            self.criar_aba_editor(path, content)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Could not open file: {exc}")

    def criar_aba_editor(self, path, content, forced_name=None):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)

        toolbar = QHBoxLayout()

        btn_run = QPushButton("Run")
        btn_run.clicked.connect(self.run_code)
        btn_run.setStyleSheet("QPushButton { background-color: #28a745; color: #ffffff; }")
        toolbar.addWidget(btn_run)

        language = detectar_linguagem_por_extensao(path) if path else (self.config_manager.get("current_language") or "python")
        language = language or "python"

        lang_combo = QComboBox()
        lang_combo.addItems(list(LANGUAGES.keys()))
        lang_combo.setCurrentText(language)
        toolbar.addWidget(lang_combo)
        toolbar.addStretch(1)

        layout.addLayout(toolbar)

        editor = Editor(self.config_manager)
        editor.set_language(language)
        editor.setPlainText(content or "")
        editor.cursorPositionChanged.connect(self.atualizar_status)
        layout.addWidget(editor)

        lang_combo.currentTextChanged.connect(lambda lang, ed=editor: self.mudar_linguagem(ed, lang))

        tab_text = forced_name or (os.path.basename(path) if path else f"Untitled-{self.untitled_count}")
        index = self.editor_tabs.addTab(container, tab_text)
        self.editor_tabs.setCurrentIndex(index)

        self.tab_meta[container] = {
            "path": path,
            "editor": editor,
            "lang_combo": lang_combo,
            "tab_name": tab_text,
        }

        if path:
            self.open_file_tabs[path] = container

        self.aplicar_tema_ao_editor(editor)
        self.atualizar_titulo()
        self.atualizar_status()

    def _close_tab_by_index(self, index, add_to_closed=True):
        widget = self.editor_tabs.widget(index)
        if widget is None:
            return

        meta = self.tab_meta.pop(widget, None)
        if add_to_closed and meta:
            editor = meta.get("editor")
            content = editor.toPlainText() if editor else ""
            self.closed_tabs.append(
                {
                    "path": meta.get("path"),
                    "content": content,
                    "lang": editor.current_language if editor else None,
                    "tab_name": meta.get("tab_name"),
                }
            )
            self.closed_tabs = self.closed_tabs[-20:]
        if meta and meta.get("path") in self.open_file_tabs:
            del self.open_file_tabs[meta["path"]]

        self.editor_tabs.removeTab(index)
        widget.deleteLater()
        self.atualizar_titulo()
        self.atualizar_status()

    def fechar_aba_atual(self):
        index = self.editor_tabs.currentIndex()
        if index >= 0:
            self._close_tab_by_index(index)

    def _close_all_tabs(self):
        while self.editor_tabs.count() > 0:
            self._close_tab_by_index(0, add_to_closed=False)

    def reopen_closed_tab(self):
        if not self.closed_tabs:
            return
        data = self.closed_tabs.pop()
        path = data.get("path")
        content = data.get("content") or ""
        tab_name = data.get("tab_name")
        if path and path in self.open_file_tabs:
            self.editor_tabs.setCurrentWidget(self.open_file_tabs[path])
            return
        self.criar_aba_editor(path, content, forced_name=tab_name)

    def salvar_arquivo(self):
        meta = self.get_current_tab_meta()
        if not meta:
            return False

        editor = meta["editor"]
        container = self.editor_tabs.currentWidget()
        index = self.editor_tabs.currentIndex()
        path = meta["path"]

        if not path:
            path, _ = QFileDialog.getSaveFileName(self, "Save File")
            if not path:
                return False

            meta["path"] = path
            self.open_file_tabs[path] = container
            self.editor_tabs.setTabText(index, os.path.basename(path))
            meta["tab_name"] = os.path.basename(path)

            detected = detectar_linguagem_por_extensao(path)
            if detected:
                meta["lang_combo"].setCurrentText(detected)

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(editor.toPlainText())
            editor.aplicar_syntax_highlight()
            self.atualizar_titulo()
            return True
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Could not save file: {exc}")
            return False

    def mudar_linguagem(self, editor, lang):
        editor.set_language(lang)
        self.config_manager.set(lang, "current_language")
        self.atualizar_status()

    def mudar_tema(self, theme_name):
        if theme_name not in THEMES:
            return
        self.config_manager.set(theme_name, "theme")
        self.aplicar_tema()

    def aplicar_tema(self):
        theme_name = self.config_manager.get("theme") or "dark"
        theme = THEMES.get(theme_name, THEMES["dark"])

        self.setStyleSheet(
            "QMainWindow, QWidget {"
            f"background-color: {theme['bg']};"
            f"color: {theme['fg']};"
            "}"
            "QMenuBar {"
            f"background-color: {theme['sidebar_bg']};"
            f"color: {theme['fg']};"
            "}"
            "QMenuBar::item:selected {"
            f"background-color: {theme['select_bg']};"
            "}"
            "QMenu {"
            f"background-color: {theme['sidebar_bg']};"
            f"color: {theme['fg']};"
            "}"
            "QMenu::item:selected {"
            f"background-color: {theme['select_bg']};"
            "}"
            "QTabWidget::pane {"
            f"border: 1px solid {theme['border']};"
            "}"
            "QTabBar::tab {"
            f"background-color: {theme['sidebar_bg']};"
            f"color: {theme['fg']};"
            f"border: 1px solid {theme['border']};"
            "padding: 6px 10px;"
            "}"
            "QTabBar::tab:selected {"
            f"background-color: {theme['editor_bg']};"
            "}"
            "QPushButton {"
            f"background-color: {theme['accent']};"
            "color: #ffffff;"
            "border: none;"
            "padding: 6px 10px;"
            "border-radius: 4px;"
            "}"
            "QPushButton:hover {"
            f"background-color: {theme['accent_hover']};"
            "}"
            "QLineEdit, QTextEdit, QComboBox {"
            f"background-color: {theme['entry_bg']};"
            f"color: {theme['fg']};"
            f"border: 1px solid {theme['border']};"
            "padding: 4px;"
            "}"
            "QSplitter::handle {"
            f"background-color: {theme['border']};"
            "width: 4px;"
            "}"
            "QStatusBar {"
            f"background-color: {theme['sidebar_bg']};"
            f"color: {theme['fg']};"
            "}"
        )

        self.explorer.apply_theme(theme)
        for meta in self.tab_meta.values():
            self.aplicar_tema_ao_editor(meta["editor"])

    def aplicar_tema_ao_editor(self, editor):
        theme_name = self.config_manager.get("theme") or "dark"
        editor.apply_theme(THEMES.get(theme_name, THEMES["dark"]))

    def write_to_output(self, text):
        self.output_received.emit(text)

    def _safe_write_to_output(self, text):
        target = self.output_box if self.main_tabs.currentWidget() == self.tab_output else self.term_output
        cursor = target.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        target.setTextCursor(cursor)
        target.ensureCursorVisible()

    def atualizar_titulo(self):
        meta = self.get_current_tab_meta()
        title = "LCoder IDE"
        if meta:
            path = meta.get("path")
            tab_name = meta.get("tab_name")
            title += f" - {os.path.basename(path) if path else tab_name}"
        self.setWindowTitle(title)

    def atualizar_status(self):
        editor = self.get_current_editor()
        if not editor:
            self.statusBar().showMessage("Ready")
            return

        line, col = editor.cursor_position()
        lang = editor.current_language
        self.statusBar().showMessage(f"Language: {lang.upper()}  |  Line: {line}  |  Col: {col}")

    def abrir_pasta(self):
        path = QFileDialog.getExistingDirectory(self, "Open Folder")
        if path:
            self._close_all_tabs()
            self.explorer.set_root_path(path)
            self._add_recent_folder(path)
            data = self._load_workspace_file(path)
            if data:
                self._apply_workspace_data(data)

    def run_code(self):
        editor = self.get_current_editor()
        if not editor:
            return
        if not self.salvar_arquivo():
            return

        meta = self.get_current_tab_meta()
        path = meta.get("path") if meta else None
        if path and os.path.exists(path):
            self.main_tabs.setCurrentWidget(self.tab_output)
            self.output_box.clear()
            self.process_manager.run_code(editor.current_language, path, self.config_manager)

    def send_terminal_command(self):
        cmd = self.term_entry.text().strip()
        if not cmd:
            return

        if not self.process_manager.terminal_process:
            editor = self.get_current_editor()
            lang = editor.current_language if editor else "python"
            self.process_manager.start_terminal(lang, self.config_manager)

        self.process_manager.send_terminal_command(cmd)
        if not self._terminal_history or self._terminal_history[-1] != cmd:
            self._terminal_history.append(cmd)
        self._terminal_history_index = len(self._terminal_history)
        self.term_entry.clear()
        self.main_tabs.setCurrentWidget(self.tab_terminal)

    def eventFilter(self, obj, event):
        if obj == self.term_entry and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Up:
                if not self._terminal_history:
                    return False
                if self._terminal_history_index == -1:
                    self._terminal_history_index = len(self._terminal_history) - 1
                else:
                    self._terminal_history_index = max(0, self._terminal_history_index - 1)
                self.term_entry.setText(self._terminal_history[self._terminal_history_index])
                self.term_entry.setCursorPosition(len(self.term_entry.text()))
                return True
            if event.key() == Qt.Key_Down:
                if not self._terminal_history:
                    return False
                if self._terminal_history_index == -1:
                    return False
                self._terminal_history_index = min(len(self._terminal_history), self._terminal_history_index + 1)
                if self._terminal_history_index >= len(self._terminal_history):
                    self.term_entry.clear()
                else:
                    self.term_entry.setText(self._terminal_history[self._terminal_history_index])
                    self.term_entry.setCursorPosition(len(self.term_entry.text()))
                return True
        return super().eventFilter(obj, event)

    def _find_in_editor(self, editor, search_text, regex=False, case_sensitive=False, backwards=False):
        if not search_text:
            return None
        flags = QTextDocument.FindFlags()
        if case_sensitive:
            flags |= QTextDocument.FindCaseSensitively
        if backwards:
            flags |= QTextDocument.FindBackward

        cursor = editor.textCursor()
        if regex:
            pattern = QRegularExpression(search_text)
            if not case_sensitive:
                pattern.setPatternOptions(QRegularExpression.CaseInsensitiveOption)
            found = editor.document().find(pattern, cursor, flags)
        else:
            found = editor.document().find(search_text, cursor, flags)

        if found.isNull():
            start_pos = editor.document().characterCount() - 1 if backwards else 0
            if regex:
                pattern = QRegularExpression(search_text)
                if not case_sensitive:
                    pattern.setPatternOptions(QRegularExpression.CaseInsensitiveOption)
                found = editor.document().find(pattern, start_pos, flags)
            else:
                found = editor.document().find(search_text, start_pos, flags)

        if not found.isNull():
            editor.setTextCursor(found)
            editor.centerCursor()
            return found
        return None

    def show_find_dialog(self):
        editor = self.get_current_editor()
        if not editor:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Find & Replace")
        dialog.resize(420, 140)

        layout = QFormLayout(dialog)
        find_entry = QLineEdit()
        replace_entry = QLineEdit()
        regex_box = QCheckBox("Regex")
        case_box = QCheckBox("Case sensitive")
        layout.addRow("Find:", find_entry)
        layout.addRow("Replace:", replace_entry)
        layout.addRow(regex_box, case_box)

        buttons = QHBoxLayout()
        btn_find = QPushButton("Find Next")
        btn_prev = QPushButton("Find Prev")
        btn_replace = QPushButton("Replace")
        btn_replace_all = QPushButton("Replace All")
        buttons.addWidget(btn_find)
        buttons.addWidget(btn_prev)
        buttons.addWidget(btn_replace)
        buttons.addWidget(btn_replace_all)
        layout.addRow(buttons)

        def find_next():
            text = find_entry.text()
            if text:
                self._find_in_editor(
                    editor,
                    text,
                    regex=regex_box.isChecked(),
                    case_sensitive=case_box.isChecked(),
                    backwards=False,
                )

        def find_prev():
            text = find_entry.text()
            if text:
                self._find_in_editor(
                    editor,
                    text,
                    regex=regex_box.isChecked(),
                    case_sensitive=case_box.isChecked(),
                    backwards=True,
                )

        def replace():
            search_text = find_entry.text()
            replace_text = replace_entry.text()
            if not search_text:
                return

            cursor = editor.textCursor()
            if cursor.hasSelection():
                cursor.insertText(replace_text)
            self._find_in_editor(
                editor,
                search_text,
                regex=regex_box.isChecked(),
                case_sensitive=case_box.isChecked(),
                backwards=False,
            )

        def replace_all():
            search_text = find_entry.text()
            replace_text = replace_entry.text()
            if not search_text:
                return

            doc = editor.document()
            flags = QTextDocument.FindFlags()
            if case_box.isChecked():
                flags |= QTextDocument.FindCaseSensitively

            cursor = QTextCursor(doc)
            cursor.beginEditBlock()
            count = 0
            if regex_box.isChecked():
                pattern = QRegularExpression(search_text)
                if not case_box.isChecked():
                    pattern.setPatternOptions(QRegularExpression.CaseInsensitiveOption)
                while True:
                    cursor = doc.find(pattern, cursor, flags)
                    if cursor.isNull():
                        break
                    cursor.insertText(replace_text)
                    count += 1
            else:
                while True:
                    cursor = doc.find(search_text, cursor, flags)
                    if cursor.isNull():
                        break
                    cursor.insertText(replace_text)
                    count += 1
            cursor.endEditBlock()
            self.statusBar().showMessage(f"Replaced {count} occurrence(s).", 3000)

        btn_find.clicked.connect(find_next)
        btn_prev.clicked.connect(find_prev)
        btn_replace.clicked.connect(replace)
        btn_replace_all.clicked.connect(replace_all)
        dialog.exec()

    def show_goto_line_dialog(self):
        editor = self.get_current_editor()
        if not editor:
            return

        max_line = editor.blockCount()
        line, ok = QInputDialog.getInt(self, "Go to Line", "Line number:", 1, 1, max_line, 1)
        if not ok:
            return

        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.Start)
        cursor.movePosition(QTextCursor.Down, QTextCursor.MoveAnchor, line - 1)
        editor.setTextCursor(cursor)
        editor.centerCursor()

    def show_theme_editor(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Theme Editor")
        dialog.resize(520, 620)

        theme_name = self.config_manager.get("theme") or "dark"
        theme = THEMES.get(theme_name, THEMES["dark"]).copy()

        root_layout = QVBoxLayout(dialog)
        scroll = QScrollArea(dialog)
        scroll.setWidgetResizable(True)
        content = QWidget()
        grid = QGridLayout(content)
        scroll.setWidget(content)
        root_layout.addWidget(scroll)

        entries = {}
        row = 0
        for key, value in theme.items():
            if isinstance(value, str) and value.startswith("#"):
                grid.addWidget(QLabel(key), row, 0)
                entry = QLineEdit(value)
                grid.addWidget(entry, row, 1)
                entries[key] = entry
                row += 1

        btn_apply = QPushButton("Apply Custom Theme")
        root_layout.addWidget(btn_apply)

        def save_theme():
            for key, entry in entries.items():
                theme[key] = entry.text().strip() or theme[key]
            THEMES["custom"] = theme
            self._rebuild_theme_menu()
            self.mudar_tema("custom")
            QMessageBox.information(self, "Success", "Custom theme applied!")

        btn_apply.clicked.connect(save_theme)
        dialog.exec()

    def closeEvent(self, event):
        self._save_session()
        self.config_manager.set(self.width(), "window", "width")
        self.config_manager.set(self.height(), "window", "height")
        if self.extension_manager:
            self.extension_manager.deactivate_all()
        self.process_manager.stop_terminal()
        super().closeEvent(event)
