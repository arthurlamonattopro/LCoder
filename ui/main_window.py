import os
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from ui.editor import Editor
from ui.explorer import Explorer
from core.themes import THEMES, UI_CONFIG
from core.languages import LANGUAGES, detectar_linguagem_por_extensao
from utils.process_mgr import ProcessManager

class MainWindow(ctk.CTk):
    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager
        self.editors = {} # path -> editor instance
        self.process_manager = ProcessManager(self.write_to_output)
        
        # Configuração básica da janela
        self.title("LCoder IDE 🚀")
        self.geometry(f"{self.config_manager.get('window', 'width')}x{self.config_manager.get('window', 'height')}")
        
        # Configuração do CustomTkinter
        ctk.set_appearance_mode(self.config_manager.get("theme"))
        
        self.setup_ui()
        self.aplicar_tema()
        self.atualizar_titulo()

    def setup_ui(self):
        self.menubar = tk.Menu(self)
        self.config(menu=self.menubar)
        self.setup_menus()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.paned_window = tk.PanedWindow(self, orient="horizontal", sashwidth=4, bg=self.config_manager.get("theme") == "dark" and "#333333" or "#e5e5e5")
        self.paned_window.grid(row=0, column=0, sticky="nsew")

        # Sidebar
        self.sidebar_frame = ctk.CTkFrame(self.paned_window, width=260, corner_radius=0)
        self.sidebar_frame.grid_rowconfigure(1, weight=1)
        self.sidebar_frame.grid_columnconfigure(0, weight=1)

        self.sidebar_label = ctk.CTkLabel(self.sidebar_frame, text="EXPLORER", font=UI_CONFIG["font_bold"])
        self.sidebar_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        self.explorer_container = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.explorer_container.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        self.explorer = Explorer(self.explorer_container, self.config_manager)
        self.explorer.pack(fill="both", expand=True)

        # Content Area
        self.content_frame = ctk.CTkFrame(self.paned_window, corner_radius=0, fg_color="transparent")
        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)

        self.paned_window.add(self.sidebar_frame)
        self.paned_window.add(self.content_frame)

        # Tabview for Editors/Output/Terminal
        self.main_tabs = ctk.CTkTabview(self.content_frame, corner_radius=UI_CONFIG["corner_radius"])
        self.main_tabs.grid(row=0, column=0, sticky="nsew")
        
        self.tab_editors = self.main_tabs.add("Editors")
        self.tab_output = self.main_tabs.add("Output")
        self.tab_terminal = self.main_tabs.add("Terminal")

        # Editor Tabview (Nested)
        self.editor_tabs = ctk.CTkTabview(self.tab_editors, corner_radius=0)
        self.editor_tabs.pack(fill="both", expand=True)

        self.setup_output_tab()
        self.setup_terminal_tab()

        # Status Bar
        self.status_bar = ctk.CTkFrame(self, height=25, corner_radius=0)
        self.status_bar.grid(row=1, column=0, sticky="ew")
        self.status_label = ctk.CTkLabel(self.status_bar, text="Ready", font=("Segoe UI", 10))
        self.status_label.pack(side="left", padx=20)

    def setup_output_tab(self):
        self.tab_output.grid_rowconfigure(0, weight=1)
        self.tab_output.grid_columnconfigure(0, weight=1)
        self.output_box = tk.Text(self.tab_output, state="disabled", wrap="word", relief="flat", padx=10, pady=10)
        self.output_box.grid(row=0, column=0, sticky="nsew")
        self.out_scroll = ctk.CTkScrollbar(self.tab_output, command=self.output_box.yview)
        self.out_scroll.grid(row=0, column=1, sticky="ns")
        self.output_box.configure(yscrollcommand=self.out_scroll.set)

    def setup_terminal_tab(self):
        self.tab_terminal.grid_rowconfigure(1, weight=1)
        self.tab_terminal.grid_columnconfigure(0, weight=1)
        self.term_input_frame = ctk.CTkFrame(self.tab_terminal, fg_color="transparent")
        self.term_input_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.term_entry = ctk.CTkEntry(self.term_input_frame, placeholder_text="Enter command...", height=35)
        self.term_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.term_entry.bind("<Return>", lambda e: self.send_terminal_command())
        self.btn_send = ctk.CTkButton(self.term_input_frame, text="Send", width=80, command=self.send_terminal_command)
        self.btn_send.pack(side="right")
        self.term_output = tk.Text(self.tab_terminal, state="disabled", wrap="word", relief="flat", padx=10, pady=10)
        self.term_output.grid(row=1, column=0, sticky="nsew")
        self.term_scroll = ctk.CTkScrollbar(self.tab_terminal, command=self.term_output.yview)
        self.term_scroll.grid(row=1, column=1, sticky="ns")
        self.term_output.configure(yscrollcommand=self.term_scroll.set)

    def setup_menus(self):
        file_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New File", command=self.novo_arquivo, accelerator="Ctrl+N")
        file_menu.add_command(label="Open File", command=self.abrir_arquivo, accelerator="Ctrl+O")
        file_menu.add_command(label="Save", command=self.salvar_arquivo, accelerator="Ctrl+S")
        file_menu.add_command(label="Close Tab", command=self.fechar_aba_atual, accelerator="Ctrl+W")
        file_menu.add_separator()
        file_menu.add_command(label="Open Folder", command=self.abrir_pasta)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)

        edit_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Find", command=self.show_find_dialog, accelerator="Ctrl+F")
        
        theme_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Theme", menu=theme_menu)
        for t in THEMES.keys():
            theme_menu.add_command(label=t.title(), command=lambda tema=t: self.mudar_tema(tema))
        theme_menu.add_separator()
        theme_menu.add_command(label="Theme Editor", command=self.show_theme_editor)

        self.bind("<Control-n>", lambda e: self.novo_arquivo())
        self.bind("<Control-o>", lambda e: self.abrir_arquivo())
        self.bind("<Control-s>", lambda e: self.salvar_arquivo())
        self.bind("<Control-w>", lambda e: self.fechar_aba_atual())
        self.bind("<Control-f>", lambda e: self.show_find_dialog())

    def get_current_editor(self):
        tab_name = self.editor_tabs.get()
        if tab_name in self.editors:
            return self.editors[tab_name]
        return None

    def novo_arquivo(self):
        name = f"Untitled-{len(self.editors)+1}"
        self.criar_aba_editor(name, None)

    def abrir_arquivo(self):
        path = filedialog.askopenfilename()
        if path:
            self.abrir_arquivo_por_caminho(path)

    def abrir_arquivo_por_caminho(self, path):
        if path in self.editors:
            self.editor_tabs.set(path)
            return
        
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            self.criar_aba_editor(path, content)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file: {e}")

    def criar_aba_editor(self, path, content):
        display_name = os.path.basename(path) if path else path
        tab = self.editor_tabs.add(path)
        
        # Toolbar for the tab
        toolbar = ctk.CTkFrame(tab, fg_color="transparent")
        toolbar.pack(side="top", fill="x", padx=5, pady=5)
        
        btn_run = ctk.CTkButton(toolbar, text="▶ Run", width=60, command=self.run_code, fg_color="#28a745", hover_color="#218838")
        btn_run.pack(side="left", padx=2)
        
        lang = detectar_linguagem_por_extensao(path) if path else "python"
        lang_var = tk.StringVar(value=lang)
        lang_menu = ctk.CTkOptionMenu(toolbar, variable=lang_var, values=list(LANGUAGES.keys()), width=100, command=lambda l: self.mudar_linguagem(l))
        lang_menu.pack(side="left", padx=5)

        editor = Editor(tab, self.config_manager, wrap="none", undo=True)
        editor.pack(fill="both", expand=True)
        
        if content:
            editor.insert("1.0", content)
        
        editor.current_language = lang
        editor.aplicar_syntax_highlight()
        
        self.editors[path] = editor
        self.editor_tabs.set(path)
        self.aplicar_tema_ao_editor(editor)
        self.atualizar_titulo()

    def fechar_aba_atual(self):
        path = self.editor_tabs.get()
        if path in self.editors:
            self.editor_tabs.delete(path)
            del self.editors[path]
            self.atualizar_titulo()

    def salvar_arquivo(self):
        editor = self.get_current_editor()
        if not editor: return
        
        path = self.editor_tabs.get()
        if not path or not os.path.exists(path):
            path = filedialog.asksaveasfilename()
            if not path: return
            
            # Update tab name
            content = editor.get("1.0", "end-1c")
            self.fechar_aba_atual()
            self.criar_aba_editor(path, content)
            editor = self.editors[path]

        try:
            content = editor.get("1.0", "end-1c")
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            editor.aplicar_syntax_highlight()
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Could not save file: {e}")
            return False

    def mudar_linguagem(self, lang):
        editor = self.get_current_editor()
        if editor:
            editor.current_language = lang
            editor.aplicar_syntax_highlight()
            self.atualizar_status()

    def mudar_tema(self, theme_name):
        self.config_manager.set(theme_name, "theme")
        ctk.set_appearance_mode(theme_name)
        self.aplicar_tema()

    def aplicar_tema(self):
        theme_name = self.config_manager.get("theme")
        theme = THEMES[theme_name]
        
        for editor in self.editors.values():
            self.aplicar_tema_ao_editor(editor)
        
        self.output_box.config(bg=theme["output_bg"], fg=theme["fg"])
        self.term_output.config(bg=theme["output_bg"], fg=theme["fg"])
        
        style = tk.ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background=theme["sidebar_bg"], foreground=theme["fg"], fieldbackground=theme["sidebar_bg"], borderwidth=0)
        style.map("Treeview", background=[('selected', theme["select_bg"])])

    def aplicar_tema_ao_editor(self, editor):
        theme_name = self.config_manager.get("theme")
        theme = THEMES[theme_name]
        editor.config(bg=theme["editor_bg"], fg=theme["fg"], insertbackground=theme["fg_active"], selectbackground=theme["select_bg"])
        editor.aplicar_syntax_highlight()

    def write_to_output(self, text):
        self.after(0, self._safe_write_to_output, text)

    def _safe_write_to_output(self, text):
        target = self.output_box if self.main_tabs.get() == "Output" else self.term_output
        target.config(state="normal")
        target.insert("end", text)
        target.see("end")
        target.config(state="disabled")

    def atualizar_titulo(self):
        path = self.editor_tabs.get()
        title = "LCoder IDE"
        if path:
            title += f" - {os.path.basename(path)}"
        self.title(title)

    def atualizar_status(self):
        editor = self.get_current_editor()
        if not editor: return
        pos = editor.index("insert")
        line, col = map(int, pos.split('.'))
        lang = editor.current_language
        status = f"Language: {lang.upper()}  |  Line: {line}  |  Col: {col}"
        self.status_label.configure(text=status)

    def abrir_pasta(self):
        path = filedialog.askdirectory()
        if path:
            self.explorer.set_root_path(path)

    def run_code(self):
        editor = self.get_current_editor()
        if not editor: return
        if not self.salvar_arquivo(): return
        
        path = self.editor_tabs.get()
        if path and os.path.exists(path):
            self.main_tabs.set("Output")
            self.output_box.config(state="normal")
            self.output_box.delete("1.0", "end")
            self.output_box.config(state="disabled")
            self.process_manager.run_code(editor.current_language, path, self.config_manager)

    def send_terminal_command(self):
        cmd = self.term_entry.get()
        if cmd:
            if not self.process_manager.terminal_process:
                editor = self.get_current_editor()
                lang = editor.current_language if editor else "python"
                self.process_manager.start_terminal(lang, self.config_manager)
            self.process_manager.send_terminal_command(cmd)
            self.term_entry.delete(0, "end")
            self.main_tabs.set("Terminal")

    def show_find_dialog(self):
        editor = self.get_current_editor()
        if not editor: return
        
        dialog = ctk.CTkToplevel(self)
        dialog.title("Find & Replace")
        dialog.geometry("400x200")
        dialog.attributes("-topmost", True)

        ctk.CTkLabel(dialog, text="Find:").grid(row=0, column=0, padx=10, pady=10)
        find_entry = ctk.CTkEntry(dialog, width=200)
        find_entry.grid(row=0, column=1, padx=10, pady=10)

        ctk.CTkLabel(dialog, text="Replace:").grid(row=1, column=0, padx=10, pady=10)
        replace_entry = ctk.CTkEntry(dialog, width=200)
        replace_entry.grid(row=1, column=1, padx=10, pady=10)

        def find_next():
            search_text = find_entry.get()
            if search_text:
                start_pos = editor.text.index("insert")
                pos = editor.text.search(search_text, start_pos, stopindex=tk.END)
                if not pos:
                    pos = editor.text.search(search_text, "1.0", stopindex=start_pos)
                if pos:
                    end_pos = f"{pos} + {len(search_text)}c"
                    editor.text.tag_remove("sel", "1.0", tk.END)
                    editor.text.tag_add("sel", pos, end_pos)
                    editor.text.mark_set("insert", end_pos)
                    editor.text.see(pos)

        def replace():
            search_text = find_entry.get()
            replace_text = replace_entry.get()
            if search_text:
                try:
                    sel_start = editor.text.index("sel.first")
                    sel_end = editor.text.index("sel.last")
                    if editor.text.get(sel_start, sel_end) == search_text:
                        editor.text.delete(sel_start, sel_end)
                        editor.text.insert(sel_start, replace_text)
                        find_next()
                except tk.TclError:
                    find_next()

        ctk.CTkButton(dialog, text="Find Next", command=find_next).grid(row=2, column=0, padx=10, pady=10)
        ctk.CTkButton(dialog, text="Replace", command=replace).grid(row=2, column=1, padx=10, pady=10)

    def show_theme_editor(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Theme Editor")
        dialog.geometry("500x600")
        
        theme_name = self.config_manager.get("theme")
        theme = THEMES[theme_name].copy()
        
        scrollable = ctk.CTkScrollableFrame(dialog)
        scrollable.pack(fill="both", expand=True, padx=10, pady=10)
        
        entries = {}
        row = 0
        for key, val in theme.items():
            if isinstance(val, str) and val.startswith("#"):
                ctk.CTkLabel(scrollable, text=key).grid(row=row, column=0, padx=5, pady=2, sticky="w")
                entry = ctk.CTkEntry(scrollable, width=100)
                entry.insert(0, val)
                entry.grid(row=row, column=1, padx=5, pady=2)
                entries[key] = entry
                row += 1
        
        def save_theme():
            for key, entry in entries.items():
                theme[key] = entry.get()
            THEMES["custom"] = theme
            self.mudar_tema("custom")
            messagebox.showinfo("Success", "Custom theme applied!")
            
        ctk.CTkButton(dialog, text="Apply Custom Theme", command=save_theme).pack(pady=10)
