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
        self.arquivo_atual = None
        self.process_manager = ProcessManager(self.write_to_output)
        
        # Configuração básica da janela
        self.title("Multi-Language IDE 🚀")
        self.geometry(f"{self.config_manager.get('window', 'width')}x{self.config_manager.get('window', 'height')}")
        
        # Configuração do CustomTkinter
        ctk.set_appearance_mode(self.config_manager.get("theme"))
        
        self.setup_ui()
        self.aplicar_tema()
        self.atualizar_titulo()

    def setup_ui(self):
        # Menu Clássico (Tkinter) - CustomTkinter não tem Menu nativo
        self.menubar = tk.Menu(self)
        self.config(menu=self.menubar)
        self.setup_menus()

        # Layout Principal usando Grid
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Barra Lateral (Explorador)
        self.sidebar_frame = ctk.CTkFrame(self, width=260, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(1, weight=1)

        self.sidebar_label = ctk.CTkLabel(self.sidebar_frame, text="EXPLORER", font=UI_CONFIG["font_bold"])
        self.sidebar_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        # Container para o Treeview (Explorer)
        self.explorer_container = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.explorer_container.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        self.explorer = Explorer(self.explorer_container, self.config_manager)
        self.explorer.pack(fill="both", expand=True)

        # Área de Conteúdo (Editor + Output)
        self.content_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.content_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)

        # Tabview para Editor/Saída/Terminal
        self.tabview = ctk.CTkTabview(self.content_frame, corner_radius=UI_CONFIG["corner_radius"])
        self.tabview.grid(row=0, column=0, sticky="nsew")
        
        self.tab_editor = self.tabview.add("Editor")
        self.tab_output = self.tabview.add("Output")
        self.tab_terminal = self.tabview.add("Terminal")

        # Configuração da aba Editor
        self.setup_editor_tab()
        
        # Configuração da aba Output
        self.setup_output_tab()
        
        # Configuração da aba Terminal
        self.setup_terminal_tab()

        # Barra de Status
        self.status_bar = ctk.CTkFrame(self, height=25, corner_radius=0)
        self.status_bar.grid(row=1, column=0, columnspan=2, sticky="ew")
        self.status_label = ctk.CTkLabel(self.status_bar, text="Ready", font=("Segoe UI", 10))
        self.status_label.pack(side="left", padx=20)

    def setup_editor_tab(self):
        self.tab_editor.grid_rowconfigure(1, weight=1)
        self.tab_editor.grid_columnconfigure(0, weight=1)

        # Toolbar interna da aba editor
        self.toolbar = ctk.CTkFrame(self.tab_editor, fg_color="transparent")
        self.toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        self.btn_run = ctk.CTkButton(self.toolbar, text="▶ Run", width=80, 
                                    command=self.run_code, 
                                    fg_color="#28a745", hover_color="#218838")
        self.btn_run.pack(side="left", padx=5)

        self.lang_label = ctk.CTkLabel(self.toolbar, text="Language:")
        self.lang_label.pack(side="left", padx=(20, 5))

        self.language_var = tk.StringVar(value=self.config_manager.get("current_language"))
        self.language_menu = ctk.CTkOptionMenu(self.toolbar, variable=self.language_var,
                                              values=list(LANGUAGES.keys()),
                                              command=self.mudar_linguagem,
                                              width=120)
        self.language_menu.pack(side="left", padx=5)

        # Editor de Texto
        self.editor = Editor(self.tab_editor, self.config_manager, wrap="none", undo=True, 
                            font=UI_CONFIG["code_font"] if "code_font" in UI_CONFIG else ("Consolas", 12))
        self.editor.grid(row=1, column=0, sticky="nsew")
        
        # Scrollbars customizadas
        self.scroll_y = ctk.CTkScrollbar(self.tab_editor, command=self.editor.yview)
        self.scroll_y.grid(row=1, column=1, sticky="ns")
        self.editor.configure(yscrollcommand=self.scroll_y.set)

        self.scroll_x = ctk.CTkScrollbar(self.tab_editor, command=self.editor.xview, orientation="horizontal")
        self.scroll_x.grid(row=2, column=0, sticky="ew")
        self.editor.configure(xscrollcommand=self.scroll_x.set)

    def setup_output_tab(self):
        self.tab_output.grid_rowconfigure(0, weight=1)
        self.tab_output.grid_columnconfigure(0, weight=1)
        
        self.output_box = tk.Text(self.tab_output, state="disabled", wrap="word", 
                                 relief="flat", padx=10, pady=10)
        self.output_box.grid(row=0, column=0, sticky="nsew")
        
        self.out_scroll = ctk.CTkScrollbar(self.tab_output, command=self.output_box.yview)
        self.out_scroll.grid(row=0, column=1, sticky="ns")
        self.output_box.configure(yscrollcommand=self.out_scroll.set)

    def setup_terminal_tab(self):
        self.tab_terminal.grid_rowconfigure(1, weight=1)
        self.tab_terminal.grid_columnconfigure(0, weight=1)
        
        self.term_input_frame = ctk.CTkFrame(self.tab_terminal, fg_color="transparent")
        self.term_input_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        self.term_entry = ctk.CTkEntry(self.term_input_frame, placeholder_text="Enter command...", 
                                      height=35)
        self.term_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.term_entry.bind("<Return>", lambda e: self.send_terminal_command())
        
        self.btn_send = ctk.CTkButton(self.term_input_frame, text="Send", width=80, 
                                     command=self.send_terminal_command)
        self.btn_send.pack(side="right")

        self.term_output = tk.Text(self.tab_terminal, state="disabled", wrap="word", 
                                  relief="flat", padx=10, pady=10)
        self.term_output.grid(row=1, column=0, sticky="nsew")
        
        self.term_scroll = ctk.CTkScrollbar(self.tab_terminal, command=self.term_output.yview)
        self.term_scroll.grid(row=1, column=1, sticky="ns")
        self.term_output.configure(yscrollcommand=self.term_scroll.set)

    def setup_menus(self):
        file_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New File", command=self.novo_arquivo)
        file_menu.add_command(label="Open File", command=self.abrir_arquivo)
        file_menu.add_command(label="Save", command=self.salvar_arquivo)
        file_menu.add_separator()
        file_menu.add_command(label="Open Folder", command=self.abrir_pasta)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)

        theme_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Theme", menu=theme_menu)
        for t in THEMES.keys():
            theme_menu.add_command(label=t.title(), command=lambda tema=t: self.mudar_tema(tema))

    def mudar_linguagem(self, lang):
        self.config_manager.set(lang, "current_language")
        self.editor.current_language = lang
        self.editor.aplicar_syntax_highlight()
        self.atualizar_status()

    def mudar_tema(self, theme_name):
        self.config_manager.set(theme_name, "theme")
        ctk.set_appearance_mode(theme_name)
        self.aplicar_tema()

    def aplicar_tema(self):
        theme_name = self.config_manager.get("theme")
        theme = THEMES[theme_name]
        
        # Cores para widgets que não são do CustomTkinter
        self.editor.config(bg=theme["editor_bg"], fg=theme["fg"], 
                          insertbackground=theme["fg_active"], 
                          selectbackground=theme["select_bg"])
        
        self.output_box.config(bg=theme["output_bg"], fg=theme["fg"])
        self.term_output.config(bg=theme["output_bg"], fg=theme["fg"])
        
        # Sidebar Treeview styling (ttk)
        style = tk.ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", 
                        background=theme["sidebar_bg"], 
                        foreground=theme["fg"],
                        fieldbackground=theme["sidebar_bg"],
                        borderwidth=0)
        style.map("Treeview", background=[('selected', theme["select_bg"])])
        
        self.editor.aplicar_syntax_highlight()

    def write_to_output(self, text):
        self.after(0, self._safe_write_to_output, text)

    def _safe_write_to_output(self, text):
        # Decide qual caixa de texto atualizar (Output ou Terminal)
        target = self.output_box if self.tabview.get() == "Output" else self.term_output
        target.config(state="normal")
        target.insert("end", text)
        target.see("end")
        target.config(state="disabled")

    def atualizar_titulo(self):
        title = "Multi-Language IDE"
        if self.arquivo_atual:
            title += f" - {os.path.basename(self.arquivo_atual)}"
        self.title(title)

    def atualizar_status(self):
        pos = self.editor.index("insert")
        line, col = map(int, pos.split('.'))
        lang = self.config_manager.get("current_language")
        status = f"Language: {lang.upper()}  |  Line: {line}  |  Col: {col}"
        self.status_label.configure(text=status)

    def novo_arquivo(self):
        self.arquivo_atual = None
        self.editor.delete("1.0", "end")
        self.atualizar_titulo()

    def abrir_arquivo(self):
        path = filedialog.askopenfilename()
        if path:
            self.abrir_arquivo_por_caminho(path)

    def abrir_arquivo_por_caminho(self, path):
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            self.editor.delete("1.0", "end")
            self.editor.insert("end", content)
            self.arquivo_atual = path
            
            lang = detectar_linguagem_por_extensao(path)
            if lang:
                self.language_var.set(lang)
                self.mudar_linguagem(lang)
                
            self.atualizar_titulo()
            self.editor.aplicar_syntax_highlight()
            self.atualizar_status()
            self.tabview.set("Editor")
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file: {e}")

    def salvar_arquivo(self):
        if not self.arquivo_atual:
            self.arquivo_atual = filedialog.asksaveasfilename()
        
        if self.arquivo_atual:
            try:
                content = self.editor.get("1.0", "end")
                with open(self.arquivo_atual, "w", encoding="utf-8") as f:
                    f.write(content)
                self.editor.aplicar_syntax_highlight()
                return True
            except Exception as e:
                messagebox.showerror("Error", f"Could not save file: {e}")
                return False
        return False

    def abrir_pasta(self):
        path = filedialog.askdirectory()
        if path:
            self.explorer.set_root_path(path)

    def run_code(self):
        if not self.salvar_arquivo():
            return
        
        if self.arquivo_atual:
            self.tabview.set("Output")
            self.output_box.config(state="normal")
            self.output_box.delete("1.0", "end")
            self.output_box.config(state="disabled")
            
            self.process_manager.run_code(
                self.config_manager.get("current_language"),
                self.arquivo_atual,
                self.config_manager
            )

    def send_terminal_command(self):
        cmd = self.term_entry.get()
        if cmd:
            if not self.process_manager.terminal_process:
                self.process_manager.start_terminal(
                    self.config_manager.get("current_language"),
                    self.config_manager
                )
            self.process_manager.send_terminal_command(cmd)
            self.term_entry.delete(0, "end")
            self.tabview.set("Terminal")
