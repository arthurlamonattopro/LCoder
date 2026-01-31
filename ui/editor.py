import re
import tkinter as tk
from core.languages import LANGUAGES
from core.themes import THEMES, UI_CONFIG

class Editor(tk.Text):
    def __init__(self, master, config_manager, **kwargs):
        # Remove custom font from kwargs to handle it manually
        font = kwargs.pop('font', UI_CONFIG["font_code"])
        super().__init__(master, font=font, relief="flat", padx=10, pady=10, **kwargs)
        
        self.config_manager = config_manager
        self.current_language = self.config_manager.get("current_language")
        self.autocomplete_window = None
        self.autocomplete_listbox = None
        self.autocomplete_start_index = None
        
        self.bind("<KeyRelease>", self.on_key_release)
        self.bind("<Key>", self.global_key_handler)

    def get_current_language_config(self):
        return LANGUAGES.get(self.current_language)

    def aplicar_syntax_highlight(self):
        lang_config = self.get_current_language_config()
        if not lang_config:
            return

        theme_name = self.config_manager.get("theme")
        theme = THEMES[theme_name]
        syntax_colors = theme["syntax"]

        # Limpa tags existentes
        for tag in self.tag_names():
            self.tag_remove(tag, "1.0", tk.END)

        content = self.get("1.0", tk.END)

        # Configura as cores das tags
        self.tag_configure("keyword", foreground=syntax_colors["keyword"])
        self.tag_configure("function", foreground=syntax_colors["function"])
        self.tag_configure("comment", foreground=syntax_colors["comment"])
        self.tag_configure("string", foreground=syntax_colors["string"])
        self.tag_configure("number", foreground=syntax_colors["number"])

        # Comentários
        prefix = re.escape(lang_config["comment_prefix"])
        for match in re.finditer(f"{prefix}.*$", content, re.MULTILINE):
            start = f"1.0 + {match.start()} chars"
            end = f"1.0 + {match.end()} chars"
            self.tag_add("comment", start, end)

        # Strings
        for quote in lang_config["string_quotes"]:
            pattern = f"{re.escape(quote)}.*?{re.escape(quote)}"
            for match in re.finditer(pattern, content, re.DOTALL):
                start = f"1.0 + {match.start()} chars"
                end = f"1.0 + {match.end()} chars"
                self.tag_add("string", start, end)

        # Palavras-chave
        for word in lang_config["keywords"]:
            pattern = r'\b' + re.escape(word) + r'\b'
            for match in re.finditer(pattern, content):
                start = f"1.0 + {match.start()} chars"
                end = f"1.0 + {match.end()} chars"
                self.tag_add("keyword", start, end)

        # Funções
        for word in lang_config["functions"]:
            pattern = r'\b' + re.escape(word) + r'\b'
            for match in re.finditer(pattern, content):
                start = f"1.0 + {match.start()} chars"
                end = f"1.0 + {match.end()} chars"
                self.tag_add("function", start, end)

        # Números
        for match in re.finditer(lang_config["number_pattern"], content):
            start = f"1.0 + {match.start()} chars"
            end = f"1.0 + {match.end()} chars"
            self.tag_add("number", start, end)

    def on_key_release(self, event):
        if event.keysym in ("Up", "Down", "Left", "Right", "Return", "Escape", "Control_L", "Control_R"):
            return
        
        if self.config_manager.get("autocomplete", "enabled"):
            self.after(self.config_manager.get("autocomplete", "delay"), self.mostrar_autocomplete)
        
        self.aplicar_syntax_highlight()
        # Notificar a janela principal para atualizar o status
        # master (tab_editor) -> tabview -> content_frame -> main_window
        try:
            main_window = self.master.master.master.master
            if hasattr(main_window, 'atualizar_status'):
                main_window.atualizar_status()
        except:
            pass

    def mostrar_autocomplete(self):
        if self.autocomplete_window:
            self.autocomplete_window.destroy()
            self.autocomplete_window = None

        try:
            pos = self.index(tk.INSERT)
            line, col = map(int, pos.split('.'))
            
            line_content = self.get(f"{line}.0", pos)
            match = re.search(r'\b(\w+)$', line_content)
            
            if not match:
                return
                
            word_start = match.group(1)
            start_col = match.start()
            
            lang_config = self.get_current_language_config()
            sugestoes = [w for w in lang_config["keywords"] + lang_config["functions"] if w.startswith(word_start)]
            
            if not sugestoes:
                return

            bbox = self.bbox(pos)
            if not bbox:
                return
                
            x, y, _, h = bbox
            root_x = self.winfo_rootx() + x
            root_y = self.winfo_rooty() + y + h

            self.autocomplete_window = tk.Toplevel(self)
            self.autocomplete_window.wm_overrideredirect(True)
            self.autocomplete_window.geometry(f"+{root_x}+{root_y}")
            
            theme_name = self.config_manager.get("theme")
            theme = THEMES[theme_name]
            
            self.autocomplete_listbox = tk.Listbox(
                self.autocomplete_window, 
                bg=theme["entry_bg"], 
                fg=theme["fg"], 
                selectbackground=theme["select_bg"], 
                activestyle="none",
                relief="flat",
                font=UI_CONFIG["font_main"],
                bd=1
            )
            for s in sugestoes:
                self.autocomplete_listbox.insert(tk.END, s)
            self.autocomplete_listbox.pack()
            self.autocomplete_listbox.select_set(0)
            self.autocomplete_start_index = f"{line}.{start_col}"
        except:
            pass

    def global_key_handler(self, event):
        if self.autocomplete_window and self.autocomplete_listbox:
            if event.keysym in ("Return", "Tab"):
                try:
                    selecionado = self.autocomplete_listbox.get(self.autocomplete_listbox.curselection())
                    self.delete(self.autocomplete_start_index, tk.INSERT)
                    self.insert(self.autocomplete_start_index, selecionado)
                except:
                    pass
                self.autocomplete_window.destroy()
                self.autocomplete_window = None
                self.autocomplete_listbox = None
                return "break"
            elif event.keysym == "Escape":
                self.autocomplete_window.destroy()
                self.autocomplete_window = None
                self.autocomplete_listbox = None
                return "break"
            elif event.keysym in ("Up", "Down"):
                try:
                    idx = self.autocomplete_listbox.curselection()[0]
                    if event.keysym == "Up" and idx > 0:
                        self.autocomplete_listbox.selection_clear(0, tk.END)
                        self.autocomplete_listbox.select_set(idx - 1)
                    elif event.keysym == "Down" and idx < self.autocomplete_listbox.size() - 1:
                        self.autocomplete_listbox.selection_clear(0, tk.END)
                        self.autocomplete_listbox.select_set(idx + 1)
                except:
                    pass
                return "break"
