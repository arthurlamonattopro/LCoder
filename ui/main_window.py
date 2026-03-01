import os

from PySide6.QtCore import Signal
from PySide6.QtGui import QAction, QTextCursor
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
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
        self.process_manager = ProcessManager(self.write_to_output)

        self.setWindowTitle("LCoder IDE")
        self.resize(
            self.config_manager.get("window", "width") or 1400,
            self.config_manager.get("window", "height") or 900,
        )

        self.output_received.connect(self._safe_write_to_output)

        self.setup_ui()
        self.setup_menus()
        self.aplicar_tema()
        self.atualizar_titulo()

    def setup_ui(self):
        splitter = QSplitter()
        self.setCentralWidget(splitter)

        sidebar = QWidget()
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(10, 10, 10, 10)

        self.sidebar_label = QLabel("EXPLORER")
        sidebar_layout.addWidget(self.sidebar_label)

        self.explorer = Explorer(self.config_manager, open_file_callback=self.abrir_arquivo_por_caminho)
        sidebar_layout.addWidget(self.explorer)

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

        file_menu = menubar.addMenu("File")
        file_menu.addAction(self._make_action("New File", "Ctrl+N", self.novo_arquivo))
        file_menu.addAction(self._make_action("Open File", "Ctrl+O", self.abrir_arquivo))
        file_menu.addAction(self._make_action("Save", "Ctrl+S", self.salvar_arquivo))
        file_menu.addAction(self._make_action("Close Tab", "Ctrl+W", self.fechar_aba_atual))
        file_menu.addSeparator()
        file_menu.addAction(self._make_action("Open Folder", None, self.abrir_pasta))
        file_menu.addSeparator()
        file_menu.addAction(self._make_action("Exit", None, self.close))

        edit_menu = menubar.addMenu("Edit")
        edit_menu.addAction(self._make_action("Find", "Ctrl+F", self.show_find_dialog))

        self.theme_menu = menubar.addMenu("Theme")
        self._rebuild_theme_menu()

    def _make_action(self, label, shortcut, callback):
        action = QAction(label, self)
        if shortcut:
            action.setShortcut(shortcut)
        action.triggered.connect(callback)
        return action

    def _rebuild_theme_menu(self):
        self.theme_menu.clear()
        for theme_name in THEMES.keys():
            self.theme_menu.addAction(
                self._make_action(theme_name.title(), None, lambda checked=False, t=theme_name: self.mudar_tema(t))
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

    def _close_tab_by_index(self, index):
        widget = self.editor_tabs.widget(index)
        if widget is None:
            return

        meta = self.tab_meta.pop(widget, None)
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
            self.explorer.set_root_path(path)

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
        self.term_entry.clear()
        self.main_tabs.setCurrentWidget(self.tab_terminal)

    def _find_next(self, editor, search_text):
        cursor = editor.textCursor()
        found = editor.document().find(search_text, cursor)
        if found.isNull():
            found = editor.document().find(search_text, 0)
        if not found.isNull():
            editor.setTextCursor(found)
            editor.centerCursor()

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
        layout.addRow("Find:", find_entry)
        layout.addRow("Replace:", replace_entry)

        buttons = QHBoxLayout()
        btn_find = QPushButton("Find Next")
        btn_replace = QPushButton("Replace")
        buttons.addWidget(btn_find)
        buttons.addWidget(btn_replace)
        layout.addRow(buttons)

        def find_next():
            text = find_entry.text()
            if text:
                self._find_next(editor, text)

        def replace():
            search_text = find_entry.text()
            replace_text = replace_entry.text()
            if not search_text:
                return

            cursor = editor.textCursor()
            if cursor.hasSelection() and cursor.selectedText() == search_text:
                cursor.insertText(replace_text)
            self._find_next(editor, search_text)

        btn_find.clicked.connect(find_next)
        btn_replace.clicked.connect(replace)
        dialog.exec()

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
        self.config_manager.set(self.width(), "window", "width")
        self.config_manager.set(self.height(), "window", "height")
        self.process_manager.stop_terminal()
        super().closeEvent(event)
