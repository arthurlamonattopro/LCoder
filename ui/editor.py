import re
import tkinter as tk
from core.languages import LANGUAGES
from core.themes import THEMES, UI_CONFIG

class LineNumbers(tk.Canvas):
    def __init__(self, master, text_widget, **kwargs):
        # Canvas doesn't support 'foreground' or 'fg' as a direct option in some versions/platforms
        # We'll handle the text color manually
        self.text_color = kwargs.pop('foreground', kwargs.pop('fg', 'black'))
        super().__init__(master, **kwargs)
        self.text_widget = text_widget
        self.redraw()

    def redraw(self):
        self.delete("all")
        i = self.text_widget.index("@0,0")
        while True:
            dline = self.text_widget.dlineinfo(i)
            if dline is None: break
            y = dline[1]
            linenum = str(i).split(".")[0]
            self.create_text(2, y, anchor="nw", text=linenum, fill=self.text_color, font=self.text_widget.cget("font"))
            i = self.text_widget.index("%s + 1 line" % i)

class Editor(tk.Frame):
    def __init__(self, master, config_manager, **kwargs):
        super().__init__(master)
        self.config_manager = config_manager
        self.current_language = self.config_manager.get("current_language")
        
        # Remove custom font from kwargs to handle it manually
        font = kwargs.pop('font', UI_CONFIG["font_code"])
        
        # Text widget
        self.text = tk.Text(self, font=font, relief="flat", padx=10, pady=10, **kwargs)
        
        # Line numbers
        self.line_numbers = LineNumbers(self, self.text, width=40, highlightthickness=0)
        self.line_numbers.pack(side="left", fill="y")
        self.text.pack(side="right", fill="both", expand=True)
        
        self.autocomplete_window = None
        self.autocomplete_listbox = None
        self.autocomplete_start_index = None
        
        self.text.bind("<KeyRelease>", self.on_key_release)
        self.text.bind("<Key>", self.global_key_handler)
        self.text.bind("<Return>", self.on_return)
        self.text.bind("<Button-1>", lambda e: self.after(10, self.match_brackets))
        
        # Sync line numbers on scroll
        self.text.bind("<MouseWheel>", lambda e: self.line_numbers.redraw())
        self.text.bind("<Button-4>", lambda e: self.line_numbers.redraw())
        self.text.bind("<Button-5>", lambda e: self.line_numbers.redraw())
        
        # Expose text methods
        self.insert = self.text.insert
        self.delete = self.text.delete
        self.get = self.text.get
        self.index = self.text.index
        self.tag_add = self.text.tag_add
        self.tag_configure = self.text.tag_configure
        self.tag_remove = self.text.tag_remove
        self.tag_names = self.text.tag_names
        self.see = self.text.see
        self.mark_set = self.text.mark_set

    def config(self, **kwargs):
        # Handle background and foreground for sub-widgets
        if 'bg' in kwargs:
            self.line_numbers.config(bg=kwargs['bg'])
        if 'fg' in kwargs:
            self.line_numbers.text_color = kwargs['fg']
            self.line_numbers.redraw()
        if 'foreground' in kwargs:
            self.line_numbers.text_color = kwargs['foreground']
            self.line_numbers.redraw()
            
        # Filter out options that tk.Text might not like if passed through Editor.config
        self.text.config(**kwargs)

    def configure(self, **kwargs):
        self.config(**kwargs)

    def yview(self, *args):
        self.text.yview(*args)
        self.line_numbers.redraw()

    def xview(self, *args):
        self.text.xview(*args)

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
            if tag != "bracket_match":
                self.tag_remove(tag, "1.0", tk.END)

        content = self.get("1.0", tk.END)

        # Configura as cores das tags
        self.tag_configure("keyword", foreground=syntax_colors["keyword"])
        self.tag_configure("function", foreground=syntax_colors["function"])
        self.tag_configure("comment", foreground=syntax_colors["comment"])
        self.tag_configure("string", foreground=syntax_colors["string"])
        self.tag_configure("number", foreground=syntax_colors["number"])
        self.tag_configure("bracket_match", background=theme["select_bg"], underline=True)

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
        
        self.line_numbers.redraw()

    def match_brackets(self):
        self.tag_remove("bracket_match", "1.0", tk.END)
        pos = self.index(tk.INSERT)
        
        # Check character before cursor
        try:
            char = self.get(f"{pos}-1c")
            if char in "([{":
                self.find_matching(pos, char, 1)
            elif char in ")]}":
                self.find_matching(f"{pos}-1c", char, -1)
        except:
            pass

    def find_matching(self, pos, char, direction):
        pairs = {"(": ")", "[": "]", "{": "}", ")": "(", "]": "[", "}": "{"}
        target = pairs[char]
        stack = 1
        
        search_pos = pos
        while True:
            if direction == 1:
                search_pos = self.index(f"{search_pos}+1c")
            else:
                search_pos = self.index(f"{search_pos}-1c")
                
            if search_pos == self.index("1.0") or search_pos == self.index("end"):
                break
                
            curr_char = self.get(search_pos)
            if curr_char == char:
                stack += 1
            elif curr_char == target:
                stack -= 1
                if stack == 0:
                    self.tag_add("bracket_match", pos if direction == 1 else f"{pos}", f"{pos}+1c" if direction == 1 else f"{pos}+1c")
                    self.tag_add("bracket_match", search_pos, f"{search_pos}+1c")
                    break

    def on_key_release(self, event):
        if event.keysym in ("Up", "Down", "Left", "Right", "Return", "Escape", "Control_L", "Control_R"):
            self.line_numbers.redraw()
            self.match_brackets()
            return
        
        if self.config_manager.get("autocomplete", "enabled"):
            self.after(self.config_manager.get("autocomplete", "delay"), self.mostrar_autocomplete)
        
        self.aplicar_syntax_highlight()
        self.match_brackets()
        
        try:
            # Find MainWindow in hierarchy
            curr = self.master
            while curr and not hasattr(curr, 'atualizar_status'):
                curr = curr.master
            if curr:
                curr.atualizar_status()
        except:
            pass

    def on_return(self, event):
        # Basic auto-indentation
        pos = self.index(tk.INSERT)
        line_content = self.get(f"{pos} linestart", pos)
        indent = re.match(r'^\s*', line_content).group(0)
        
        # If line ends with a colon (Python/Ruby style), add extra indent
        if line_content.strip().endswith(':'):
            indent += '    '
            
        self.insert(pos, '\n' + indent)
        self.see(tk.INSERT)
        self.line_numbers.redraw()
        return "break"

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

            bbox = self.text.bbox(pos)
            if not bbox:
                return
                
            x, y, _, h = bbox
            root_x = self.text.winfo_rootx() + x
            root_y = self.text.winfo_rooty() + y + h

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
                self.aplicar_syntax_highlight()
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
