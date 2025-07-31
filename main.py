import os
import shutil
import subprocess
import threading
import time
import json
from tkinter import *
from tkinter import ttk, filedialog, messagebox, simpledialog, colorchooser
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PIL import Image, ImageTk
import re

# Variáveis globais
arquivo_atual = None
root_path = None
autocomplete_window = None
autocomplete_listbox = None
autocomplete_start_index = None
config_file = "ide_config.json"
current_theme = "dark"
current_language = "lua"

# Processo do terminal
terminal_process = None
terminal_output_queue = []

# Configurações de linguagens suportadas
LANGUAGES = {
    "lua": {
        "name": "Lua",
        "extensions": [".lua"],
        "icon": "🌙",
        "executable": "lua",
        "run_args": ["{file}"],
        "repl_args": ["-e", "{code}"],
        "keywords": ["function", "end", "if", "then", "else", "elseif", "for", "while", "do", "local", "return", "break", "repeat", "until", "and", "or", "not", "nil", "true", "false"],
        "functions": ["print", "pairs", "ipairs", "next", "type", "tostring", "tonumber", "table", "string", "math", "io", "os", "require", "pcall", "xpcall", "error", "assert"],
        "comment_prefix": "--",
        "string_quotes": ["\"", "\'"],
        "number_pattern": r'\b\d+(\.\d+)?\b'
    },
    "python": {
        "name": "Python",
        "extensions": [".py"],
        "icon": "🐍",
        "executable": "python3",
        "run_args": ["{file}"],
        "repl_args": ["-c", "{code}"],
        "keywords": ["def", "class", "if", "elif", "else", "for", "while", "try", "except", "finally", "with", "as", "import", "from", "return", "yield", "break", "continue", "pass", "lambda", "and", "or", "not", "in", "is", "True", "False", "None"],
        "functions": ["print", "len", "range", "enumerate", "zip", "map", "filter", "sorted", "sum", "max", "min", "abs", "round", "int", "float", "str", "list", "dict", "set", "tuple", "type", "isinstance", "hasattr", "getattr", "setattr"],
        "comment_prefix": "#",
        "string_quotes": ["\"", "\\'", "\"\"\"", "\\'\\'\\'"],
        "number_pattern": r'\b\d+(\.\d+)?\b'
    },
    "javascript": {
        "name": "JavaScript (Node.js)",
        "extensions": [".js"],
        "icon": "🟨",
        "executable": "node",
        "run_args": ["{file}"],
        "repl_args": ["-e", "{code}"],
        "keywords": ["function", "var", "let", "const", "if", "else", "for", "while", "do", "switch", "case", "default", "break", "continue", "return", "try", "catch", "finally", "throw", "new", "this", "class", "extends", "import", "export", "async", "await", "true", "false", "null", "undefined"],
        "functions": ["console.log", "parseInt", "parseFloat", "isNaN", "isFinite", "setTimeout", "setInterval", "clearTimeout", "clearInterval", "JSON.parse", "JSON.stringify", "Object.keys", "Object.values", "Array.isArray"],
        "comment_prefix": "//",
        "string_quotes": ["\"", "\\'", "`"],
        "number_pattern": r'\b\d+(\.\d+)?\b'
    },
    "ruby": {
        "name": "Ruby",
        "extensions": [".rb"],
        "icon": "💎",
        "executable": "ruby",
        "run_args": ["{file}"],
        "repl_args": ["-e", "{code}"],
        "keywords": ["def", "class", "module", "if", "elsif", "else", "unless", "case", "when", "for", "while", "until", "do", "begin", "rescue", "ensure", "end", "return", "yield", "break", "next", "redo", "retry", "super", "self", "true", "false", "nil", "and", "or", "not"],
        "functions": ["puts", "print", "p", "gets", "chomp", "to_s", "to_i", "to_f", "length", "size", "empty?", "nil?", "class", "methods", "respond_to?", "send", "eval", "require", "load"],
        "comment_prefix": "#",
        "string_quotes": ["\"", "\'"],
        "number_pattern": r'\b\d+(\.\d+)?\b'
    },
    "php": {
        "name": "PHP",
        "extensions": [".php"],
        "icon": "🐘",
        "executable": "php",
        "run_args": ["{file}"],
        "repl_args": ["-r", "{code}"],
        "keywords": ["function", "class", "interface", "trait", "if", "elseif", "else", "switch", "case", "default", "for", "foreach", "while", "do", "try", "catch", "finally", "throw", "return", "break", "continue", "public", "private", "protected", "static", "abstract", "final", "const", "var", "true", "false", "null"],
        "functions": ["echo", "print", "var_dump", "print_r", "strlen", "substr", "strpos", "str_replace", "explode", "implode", "array", "count", "is_array", "isset", "empty", "unset", "include", "require", "include_once", "require_once"],
        "comment_prefix": "//",
        "string_quotes": ["\"", "\'"],
        "number_pattern": r'\b\d+(\.\d+)?\b'
    },
    "perl": {
        "name": "Perl",
        "extensions": [".pl"],
        "icon": "🐪",
        "executable": "perl",
        "run_args": ["{file}"],
        "repl_args": ["-e", "{code}"],
        "keywords": ["sub", "if", "elsif", "else", "unless", "for", "foreach", "while", "until", "do", "given", "when", "default", "return", "last", "next", "redo", "retry", "super", "self", "true", "false", "nil", "and", "or", "not"],
        "functions": ["print", "say", "printf", "sprintf", "chomp", "chop", "length", "substr", "index", "rindex", "split", "join", "grep", "map", "sort", "reverse", "push", "pop", "shift", "unshift", "splice"],
        "comment_prefix": "#",
        "string_quotes": ["\"", "\'"],
        "number_pattern": r'\b\d+(\.\d+)?\b'
    }
}

# Temas predefinidos
themes = {
    "dark": {
        "bg": "#1e1e1e",
        "fg": "#ffffff",
        "select_bg": "#264f78",
        "select_fg": "#ffffff",
        "editor_bg": "#1e1e1e",
        "editor_fg": "#d4d4d4",
        "output_bg": "#0c0c0c",
        "output_fg": "#cccccc",
        "tree_bg": "#252526",
        "tree_fg": "#cccccc",
        "button_bg": "#0e639c",
        "button_fg": "#ffffff",
        "entry_bg": "#3c3c3c",
        "entry_fg": "#ffffff",
        "syntax": {
            "keyword": "#569cd6",
            "function": "#dcdcaa",
            "comment": "#6a9955",
            "string": "#ce9178",
            "number": "#b5cea8"
        }
    },
    "light": {
        "bg": "#ffffff",
        "fg": "#000000",
        "select_bg": "#0078d4",
        "select_fg": "#ffffff",
        "editor_bg": "#ffffff",
        "editor_fg": "#000000",
        "output_bg": "#f8f8f8",
        "output_fg": "#000000",
        "tree_bg": "#f3f3f3",
        "tree_fg": "#000000",
        "button_bg": "#0078d4",
        "button_fg": "#ffffff",
        "entry_bg": "#ffffff",
        "entry_fg": "#000000",
        "syntax": {
            "keyword": "#0000ff",
            "function": "#795e26",
            "comment": "#008000",
            "string": "#a31515",
            "number": "#098658"
        }
    },
    "monokai": {
        "bg": "#272822",
        "fg": "#f8f8f2",
        "select_bg": "#49483e",
        "select_fg": "#f8f8f2",
        "editor_bg": "#272822",
        "editor_fg": "#f8f8f2",
        "output_bg": "#1e1f1c",
        "output_fg": "#f8f8f2",
        "tree_bg": "#3e3d32",
        "tree_fg": "#f8f8f2",
        "button_bg": "#a6e22e",
        "button_fg": "#272822",
        "entry_bg": "#3e3d32",
        "entry_fg": "#f8f8f2",
        "syntax": {
            "keyword": "#f92672",
            "function": "#a6e22e",
            "comment": "#75715e",
            "string": "#e6db74",
            "number": "#ae81ff"
        }
    }
}

# Configurações padrão
default_config = {
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
        "perl": {"path": ""}
    },
    "window": {
        "width": 1400,
        "height": 900,
        "maximized": False
    }
}

# Configuração atual
current_config = default_config.copy()

def encontrar_executavel(nome):
    """Encontra o executável de uma linguagem no sistema"""
    try:
        result = subprocess.run(["which", nome], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    
    # Tenta alguns caminhos comuns no Windows
    if os.name == 'nt':
        common_paths = [
            f"C:\\Program Files\\{nome}\\{nome}.exe",
            f"C:\\{nome}\\{nome}.exe",
            f"{nome}.exe"
        ]
        for path in common_paths:
            if os.path.exists(path):
                return path
    
    return nome  # Retorna o nome se não encontrar o caminho completo

def carregar_configuracao():
    """Carrega as configurações do arquivo JSON"""
    global current_config, current_theme, current_language
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
                # Mescla com configurações padrão
                def merge_config(default, loaded):
                    for key, value in loaded.items():
                        if key in default:
                            if isinstance(value, dict) and isinstance(default[key], dict):
                                merge_config(default[key], value)
                            else:
                                default[key] = value
                merge_config(current_config, loaded_config)
                current_theme = current_config.get("theme", "dark")
                current_language = current_config.get("current_language", "lua")
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao carregar configurações: {e}")

def salvar_configuracao():
    """Salva as configurações no arquivo JSON"""
    try:
        current_config["theme"] = current_theme
        current_config["current_language"] = current_language
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(current_config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao salvar configurações: {e}")

def get_current_language_config():
    """Retorna a configuração da linguagem atual"""
    return LANGUAGES.get(current_language, LANGUAGES["lua"])

def aplicar_tema():
    """Aplica o tema atual a todos os componentes"""
    theme = themes[current_theme]
    
    # Configura o estilo ttk
    style = ttk.Style()
    style.theme_use('clam')
    
    # Configura cores do notebook
    style.configure('TNotebook', background=theme["bg"])
    style.configure('TNotebook.Tab', background=theme["bg"], foreground=theme["fg"], padding=[20, 8])
    style.map('TNotebook.Tab', background=[('selected', theme["select_bg"])], foreground=[('selected', theme["select_fg"])])
    
    # Configura treeview
    style.configure('Treeview', background=theme["tree_bg"], foreground=theme["tree_fg"], fieldbackground=theme["tree_bg"])
    style.map('Treeview', background=[('selected', theme["select_bg"])], foreground=[('selected', theme["select_fg"])])
    
    # Aplica ao editor
    text_editor.config(
        bg=theme["editor_bg"],
        fg=theme["editor_fg"],
        insertbackground=theme["editor_fg"],
        selectbackground=theme["select_bg"],
        selectforeground=theme["select_fg"],
        font=(current_config["editor"]["font_family"], current_config["editor"]["font_size"])
    )
    
    # Aplica cores de sintaxe
    for tag, color in theme["syntax"].items():
        text_editor.tag_configure(tag, foreground=color)
    
    # Aplica ao output_box
    output_box.config(
        bg=theme["output_bg"],
        fg=theme["output_fg"],
        selectbackground=theme["select_bg"],
        selectforeground=theme["select_fg"],
        font=(current_config["editor"]["font_family"], current_config["editor"]["font_size"])
    )
    
    # Aplica ao terminal
    terminal_entry.config(
        bg=theme["entry_bg"],
        fg=theme["entry_fg"],
        insertbackground=theme["entry_fg"],
        selectbackground=theme["select_bg"],
        selectforeground=theme["select_fg"],
        font=(current_config["editor"]["font_family"], current_config["editor"]["font_size"])
    )
    
    # Aplica aos botões
    for widget in [run_button, terminal_run_button]:
        widget.config(
            bg=theme["button_bg"],
            fg=theme["button_fg"],
            activebackground=theme["select_bg"],
            activeforeground=theme["select_fg"],
            relief="flat",
            bd=0,
            padx=20,
            pady=8,
            font=("Segoe UI", 10)
        )
    
    # Aplica aos frames
    for frame in [editor_frame, config_frame, frame_tree, terminal_frame, status_frame]:
        frame.config(bg=theme["bg"])
    
    # Atualiza a janela principal
    root.config(bg=theme["bg"])

def mudar_tema(novo_tema):
    """Muda o tema atual"""
    global current_theme
    current_theme = novo_tema
    aplicar_tema()
    aplicar_syntax_highlight()

def mudar_linguagem(nova_linguagem):
    """Muda a linguagem atual"""
    global current_language
    current_language = nova_linguagem
    aplicar_syntax_highlight()
    atualizar_titulo()
    salvar_configuracao()

def atualizar_titulo():
    """Atualiza o título da janela com a linguagem atual"""
    lang_config = get_current_language_config()
    if arquivo_atual:
        root.title(f"{lang_config['name']} IDE {lang_config['icon']} - {os.path.basename(arquivo_atual)}")
    else:
        root.title(f"{lang_config['name']} IDE {lang_config['icon']}")

def aplicar_syntax_highlight():
    """Aplica destaque de sintaxe com base na linguagem e tema atuais"""
    lang_config = get_current_language_config()
    
    # Remove tags existentes
    for tag in ["keyword", "comment", "string", "number", "function"]:
        text_editor.tag_remove(tag, "1.0", END)

    # Aplica keywords
    for palavra in lang_config["keywords"]:
        start = "1.0"
        while True:
            pos = text_editor.search(rf'\b{re.escape(palavra)}\b', start, stopindex=END, regexp=True)
            if not pos:
                break
            end = f"{pos}+{len(palavra)}c"
            text_editor.tag_add("keyword", pos, end)
            start = end

    # Aplica functions
    for palavra in lang_config["functions"]:
        start = "1.0"
        while True:
            pos = text_editor.search(rf'\b{re.escape(palavra)}\b', start, stopindex=END, regexp=True)
            if not pos:
                break
            end = f"{pos}+{len(palavra)}c"
            text_editor.tag_add("function", pos, end)
            start = end

    # Aplica comentários
    start = "1.0"
    comment_prefix = lang_config["comment_prefix"]
    while True:
        pos = text_editor.search(comment_prefix, start, stopindex=END)
        if not pos:
            break
        linha_fim = pos.split('.')[0] + ".end"
        text_editor.tag_add("comment", pos, linha_fim)
        start = linha_fim

    # Aplica strings
    for quote in lang_config["string_quotes"]:
        start = "1.0"
        while True:
            pos = text_editor.search(quote, start, stopindex=END)
            if not pos:
                break
            if len(quote) > 1:  # Para strings multi-linha como """ ou '''
                end = text_editor.search(quote, f"{pos}+{len(quote)}c", stopindex=END)
                if end:
                    end = f"{end}+{len(quote)}c"
                else:
                    break
            else:
                end = text_editor.search(quote, f"{pos}+1c", stopindex=END)
                if end:
                    end = f"{end}+1c"
                else:
                    break
            text_editor.tag_add("string", pos, end)
            start = end

    # Aplica números
    start = "1.0"
    number_pattern = lang_config["number_pattern"]
    while True:
        pos = text_editor.search(number_pattern, start, stopindex=END, regexp=True)
        if not pos:
            break
        # Encontra o final do número
        line, col = map(int, pos.split('.'))
        text_at_pos = text_editor.get(f"{line}.{col}", f"{line}.end")
        match = re.match(number_pattern, text_at_pos)
        if match:
            end = f"{line}.{col + len(match.group())}"
            text_editor.tag_add("number", pos, end)
            start = end
        else:
            start = f"{pos}+1c"

def delayed_highlight():
    time.sleep(current_config["autocomplete"]["delay"] / 1000.0)
    root.after(0, aplicar_syntax_highlight)

def on_key_release(event):
    if event.keysym in ["Up", "Down", "Left", "Right", "BackSpace", "Return", "Tab"]:
        return
    threading.Thread(target=delayed_highlight, daemon=True).start()
    if current_config["autocomplete"]["enabled"]:
        autocomplete(event)
    atualizar_status()

def autocomplete(event):
    global autocomplete_window, autocomplete_listbox, autocomplete_start_index
    if autocomplete_window:
        autocomplete_window.destroy()
        autocomplete_window = None
        autocomplete_listbox = None

    pos = text_editor.index(INSERT)
    line, col = map(int, pos.split('.'))
    start_col = col
    while start_col > 0:
        char = text_editor.get(f"{line}.{start_col-1}")
        if not (char.isalnum() or char == "_"):
            break
        start_col -= 1
    palavra = text_editor.get(f"{line}.{start_col}", pos)
    if not palavra:
        return

    lang_config = get_current_language_config()
    sugestoes = [k for k in lang_config["keywords"] + lang_config["functions"] if k.startswith(palavra)]
    if not sugestoes:
        return

    theme = themes[current_theme]
    autocomplete_window = Toplevel(root)
    autocomplete_window.overrideredirect(True)
    autocomplete_window.attributes("-topmost", True)

    try:
        x, y, cx, cy = text_editor.bbox(f"{line}.{start_col}")
        x += root.winfo_rootx()
        y += root.winfo_rooty() + cy
        autocomplete_window.geometry(f"+{x}+{y}")
    except:
        autocomplete_window.destroy()
        autocomplete_window = None
        return

    autocomplete_listbox = Listbox(
        autocomplete_window, 
        bg=theme["entry_bg"], 
        fg=theme["entry_fg"], 
        selectbackground=theme["select_bg"], 
        activestyle="none",
        relief="flat",
        bd=1
    )
    for s in sugestoes:
        autocomplete_listbox.insert(END, s)
    autocomplete_listbox.pack()
    autocomplete_listbox.select_set(0)
    autocomplete_start_index = f"{line}.{start_col}"

def global_key_handler(event):
    global autocomplete_window, autocomplete_listbox, autocomplete_start_index
    if autocomplete_window and autocomplete_listbox:
        if event.keysym in ("Return", "Tab"):
            try:
                selecionado = autocomplete_listbox.get(autocomplete_listbox.curselection())
                text_editor.delete(autocomplete_start_index, INSERT)
                text_editor.insert(autocomplete_start_index, selecionado)
            except:
                pass
            autocomplete_window.destroy()
            autocomplete_window = None
            autocomplete_listbox = None
            return "break"
        elif event.keysym == "Escape":
            autocomplete_window.destroy()
            autocomplete_window = None
            autocomplete_listbox = None
            return "break"
        elif event.keysym == "Up":
            try:
                idx = autocomplete_listbox.curselection()[0]
                if idx > 0:
                    autocomplete_listbox.selection_clear(0, END)
                    autocomplete_listbox.select_set(idx - 1)
            except:
                pass
            return "break"
        elif event.keysym == "Down":
            try:
                idx = autocomplete_listbox.curselection()[0]
                if idx < autocomplete_listbox.size() - 1:
                    autocomplete_listbox.selection_clear(0, END)
                    autocomplete_listbox.select_set(idx + 1)
            except:
                pass
            return "break"

def atualizar_status():
    """Atualiza a barra de status"""
    try:
        pos = text_editor.index(INSERT)
        line, col = map(int, pos.split('.'))
        total_lines = int(text_editor.index(END).split('.')[0]) - 1
        
        lang_config = get_current_language_config()
        status_text = f"Linguagem: {lang_config['name']} | Linha: {line} | Coluna: {col} | Total de linhas: {total_lines}"
        if arquivo_atual:
            status_text += f" | Arquivo: {os.path.basename(arquivo_atual)}"
        
        status_label.config(text=status_text)
    except:
        pass

def detectar_linguagem_por_extensao(caminho_arquivo):
    """Detecta a linguagem baseada na extensão do arquivo"""
    ext = os.path.splitext(caminho_arquivo)[1].lower()
    for lang_key, lang_config in LANGUAGES.items():
        if ext in lang_config["extensions"]:
            return lang_key
    return current_language  # Retorna a linguagem atual se não encontrar

def montar_arvore(tree, caminho, pai=""):
    for child in tree.get_children(pai):
        tree.delete(child)
    try:
        itens = sorted(os.listdir(caminho), key=lambda x: (not os.path.isdir(os.path.join(caminho, x)), x.lower()))
    except PermissionError:
        return
    for item in itens:
        caminho_completo = os.path.join(caminho, item)
        # Adiciona ícones baseados no tipo de arquivo
        if os.path.isdir(caminho_completo):
            icon = "📁"
        else:
            ext = os.path.splitext(item)[1].lower()
            icon = "📄"  # Ícone padrão
            for lang_config in LANGUAGES.values():
                if ext in lang_config["extensions"]:
                    icon = lang_config["icon"]
                    break
            if ext in ['.txt', '.md']:
                icon = "📄"
            elif ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp']:
                icon = "🖼️"
        
        node = tree.insert(pai, "end", text=f"{icon} {item}", open=False)
        if os.path.isdir(caminho_completo):
            montar_arvore(tree, caminho_completo, node)

def caminho_do_item(tree, item_id):
    partes = []
    while item_id:
        texto = tree.item(item_id, "text")
        # Remove o ícone do texto
        nome = texto.split(" ", 1)[1] if " " in texto else texto
        partes.insert(0, nome)
        item_id = tree.parent(item_id)
    return os.path.join(root_path, *partes)

def abrir_imagem(caminho_imagem):
    try:
        img_window = Toplevel(root)
        img_window.title(f"Visualizador de Imagem - {os.path.basename(caminho_imagem)}")
        img_window.config(bg=themes[current_theme]["bg"])
        
        # Carrega e redimensiona a imagem se necessário
        img = Image.open(caminho_imagem)
        # Limita o tamanho máximo
        max_size = (800, 600)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        img_tk = ImageTk.PhotoImage(img)
        
        label = Label(img_window, image=img_tk, bg=themes[current_theme]["bg"])
        label.image = img_tk
        label.pack(padx=10, pady=10)
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao abrir imagem:\n{e}")

def limpar_selecao_e_editor():
    global arquivo_atual
    arquivo_atual = None
    try:
        tree.selection_remove(tree.selection())
    except:
        pass
    text_editor.config(state=NORMAL)
    text_editor.delete("1.0", END)
    atualizar_titulo()
    atualizar_status()

def ao_clicar(event):
    global arquivo_atual, current_language
    selecionados = tree.selection()
    if not selecionados:
        return
    item_id = selecionados[0]
    caminho_completo = caminho_do_item(tree, item_id)
    if os.path.isfile(caminho_completo):
        ext = os.path.splitext(caminho_completo)[1].lower()
        if ext in [".png", ".jpg", ".jpeg", ".gif", ".bmp"]:
            abrir_imagem(caminho_completo)
            return
        try:
            with open(caminho_completo, "r", encoding="utf-8", errors="ignore") as f:
                conteudo = f.read()
            text_editor.config(state=NORMAL)
            text_editor.delete("1.0", END)
            text_editor.insert(END, conteudo)
            arquivo_atual = caminho_completo
            
            # Detecta e muda a linguagem automaticamente
            nova_linguagem = detectar_linguagem_por_extensao(caminho_completo)
            if nova_linguagem != current_language:
                mudar_linguagem(nova_linguagem)
                language_var.set(nova_linguagem)
            
            atualizar_titulo()
            aplicar_syntax_highlight()
            atualizar_status()
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao abrir arquivo:\n{e}")

def salvar_arquivo():
    global arquivo_atual
    if arquivo_atual:
        try:
            conteudo = text_editor.get("1.0", END)
            with open(arquivo_atual, "w", encoding="utf-8") as f:
                f.write(conteudo)
            aplicar_syntax_highlight()
            messagebox.showinfo("Sucesso", "Arquivo salvo com sucesso!")
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível salvar o arquivo:\n{e}")
    else:
        salvar_como()

def salvar_como():
    global arquivo_atual
    lang_config = get_current_language_config()
    default_ext = lang_config["extensions"][0] if lang_config["extensions"] else ".txt"
    
    filetypes = [(f"Arquivos {lang_config['name']}", f"*{default_ext}")]
    filetypes.append(("Todos os arquivos", "*.*"))
    
    caminho = filedialog.asksaveasfilename(
        defaultextension=default_ext, 
        filetypes=filetypes
    )
    if caminho:
        try:
            conteudo = text_editor.get("1.0", END)
            with open(caminho, "w", encoding="utf-8") as f:
                f.write(conteudo)
            arquivo_atual = caminho
            atualizar_titulo()
            aplicar_syntax_highlight()
            atualizar_status()
            messagebox.showinfo("Sucesso", "Arquivo salvo com sucesso!")
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível salvar o arquivo:\n{e}")

def get_language_executable(language):
    """Obtém o executável configurado para uma linguagem"""
    config_path = current_config["languages"].get(language, {}).get("path", "")
    if config_path and os.path.exists(config_path):
        return config_path
    
    lang_config = LANGUAGES[language]
    return encontrar_executavel(lang_config["executable"])

def run_code():
    """Executa o código na linguagem atual"""
    lang_config = get_current_language_config()
    executable = get_language_executable(current_language)
    
    if not executable:
        messagebox.showerror("Erro", f"{lang_config['name']} não encontrado! Configure o caminho na aba Configurações.")
        return
    
    # Salva o arquivo temporário
    temp_file = f"temp_script{lang_config['extensions'][0]}"
    with open(temp_file, "w", encoding="utf-8") as f:
        f.write(text_editor.get("1.0", END))
    
    try:
        # Prepara os argumentos de execução
        run_args = [arg.format(file=temp_file) for arg in lang_config["run_args"]]
        cmd = [executable] + run_args
        
        process = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        output_box.config(state=NORMAL)
        output_box.delete("1.0", END)
        
        if process.stdout:
            output_box.insert(END, "=== SAÍDA ===\n")
            output_box.insert(END, process.stdout)
        if process.stderr:
            output_box.insert(END, "\n=== ERROS ===\n")
            output_box.insert(END, process.stderr)
        if not process.stdout and not process.stderr:
            output_box.insert(END, "Script executado sem saída.")
            
        output_box.config(state=DISABLED)
        output_box.see(END)
        
        # Remove o arquivo temporário
        try:
            os.remove(temp_file)
        except:
            pass
            
    except subprocess.TimeoutExpired:
        output_box.config(state=NORMAL)
        output_box.delete("1.0", END)
        output_box.insert(END, "Erro: Script demorou muito para executar (timeout de 30s)")
        output_box.config(state=DISABLED)
    except Exception as e:
        output_box.config(state=NORMAL)
        output_box.delete("1.0", END)
        output_box.insert(END, f"Erro ao executar {lang_config['name']}:\n{e}")
        output_box.config(state=DISABLED)

def start_terminal():
    global terminal_process
    if terminal_process and terminal_process.poll() is None:
        messagebox.showinfo("Terminal", "O terminal já está em execução.")
        return

    shell = []
    if os.name == 'nt':  # Windows
        shell = ['cmd.exe']
    else:  # Linux/Unix
        shell = ['bash'] # ou 'sh', 'zsh', dependendo do sistema

    try:
        terminal_process = subprocess.Popen(
            shell,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,  # Decodifica stdout/stderr como texto
            bufsize=1,  # Linha por linha
            universal_newlines=True # Para compatibilidade de quebra de linha
        )
        output_box.config(state=NORMAL)
        output_box.delete("1.0", END)
        output_box.insert(END, f"Terminal iniciado: {shell[0]}\n")
        output_box.config(state=DISABLED)
        output_box.see(END)

        # Inicia threads para ler a saída do terminal
        threading.Thread(target=read_stdout, daemon=True).start()
        threading.Thread(target=read_stderr, daemon=True).start()
        threading.Thread(target=check_terminal_status, daemon=True).start()

    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao iniciar terminal: {e}")

def read_stdout():
    global terminal_output_queue
    for line in iter(terminal_process.stdout.readline, ''):
        terminal_output_queue.append(line)
        root.after(10, update_terminal_output) # Atualiza a GUI na thread principal

def read_stderr():
    global terminal_output_queue
    for line in iter(terminal_process.stderr.readline, ''):
        terminal_output_queue.append(f"ERRO: {line}")
        root.after(10, update_terminal_output) # Atualiza a GUI na thread principal

def update_terminal_output():
    global terminal_output_queue
    output_box.config(state=NORMAL)
    while terminal_output_queue:
        line = terminal_output_queue.pop(0)
        output_box.insert(END, line)
    output_box.config(state=DISABLED)
    output_box.see(END)

def check_terminal_status():
    global terminal_process
    while terminal_process and terminal_process.poll() is None:
        time.sleep(1) # Verifica a cada segundo
    if terminal_process:
        output_box.config(state=NORMAL)
        output_box.insert(END, f"\nTerminal encerrado com código de saída: {terminal_process.returncode}\n")
        output_box.config(state=DISABLED)
        output_box.see(END)
        terminal_process = None

def send_terminal_command(event=None):
    global terminal_process
    if not terminal_process or terminal_process.poll() is not None:
        messagebox.showwarning("Terminal", "O terminal não está em execução. Inicie-o primeiro.")
        return

    command = terminal_entry.get().strip()
    terminal_entry.delete(0, END)
    if not command:
        return

    try:
        terminal_process.stdin.write(command + '\n')
        terminal_process.stdin.flush()
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao enviar comando: {e}")

def stop_terminal():
    global terminal_process
    if terminal_process and terminal_process.poll() is None:
        try:
            terminal_process.terminate() # Tenta terminar gentilmente
            time.sleep(0.5)
            if terminal_process.poll() is None:
                terminal_process.kill() # Se não terminar, mata o processo
            messagebox.showinfo("Terminal", "Terminal encerrado.")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao encerrar terminal: {e}")
    else:
        messagebox.showinfo("Terminal", "Nenhum terminal em execução para encerrar.")

def criar_arquivo():
    selecionados = tree.selection()
    if selecionados:
        item_id = selecionados[0]
        caminho_selecionado = caminho_do_item(tree, item_id)
        pasta_destino = caminho_selecionado if os.path.isdir(caminho_selecionado) else os.path.dirname(caminho_selecionado)
    else:
        pasta_destino = root_path
    
    lang_config = get_current_language_config()
    default_ext = lang_config["extensions"][0] if lang_config["extensions"] else ".txt"
    
    nome_arquivo = simpledialog.askstring(
        "Criar arquivo", 
        f"Nome do novo arquivo (com extensão):\nPasta: {pasta_destino}\nSugestão: arquivo{default_ext}"
    )
    if nome_arquivo:
        novo_caminho = os.path.join(pasta_destino, nome_arquivo)
        if os.path.exists(novo_caminho):
            messagebox.showerror("Erro", "Arquivo já existe.")
            return
        try:
            with open(novo_caminho, "w", encoding="utf-8") as f:
                f.write("")
            montar_arvore(tree, root_path)
            limpar_selecao_e_editor()
            messagebox.showinfo("Sucesso", f"Arquivo '{nome_arquivo}' criado com sucesso!")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao criar arquivo:\n{e}")

def excluir_item():
    item_id = tree.focus()
    if not item_id:
        messagebox.showwarning("Aviso", "Selecione um arquivo ou pasta para excluir.")
        return
    
    caminho = caminho_do_item(tree, item_id)
    nome = os.path.basename(caminho)
    
    if messagebox.askyesno("Confirmar exclusão", f"Tem certeza que deseja excluir '{nome}'?"):
        try:
            if os.path.isdir(caminho):
                shutil.rmtree(caminho)
            else:
                os.remove(caminho)
            montar_arvore(tree, root_path)
            limpar_selecao_e_editor()
            messagebox.showinfo("Sucesso", f"'{nome}' foi excluído com sucesso!")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao excluir '{nome}':\n{e}")

def criar_pasta():
    selecionados = tree.selection()
    if selecionados:
        item_id = selecionados[0]
        caminho_selecionado = caminho_do_item(tree, item_id)
        pasta_destino = caminho_selecionado if os.path.isdir(caminho_selecionado) else os.path.dirname(caminho_selecionado)
    else:
        pasta_destino = root_path
    
    nome_pasta = simpledialog.askstring(
        "Criar pasta", 
        f"Nome da nova pasta:\nPasta: {pasta_destino}"
    )
    if nome_pasta:
        novo_caminho = os.path.join(pasta_destino, nome_pasta)
        if os.path.exists(novo_caminho):
            messagebox.showerror("Erro", "Pasta já existe.")
            return
        try:
            os.makedirs(novo_caminho)
            montar_arvore(tree, root_path)
            messagebox.showinfo("Sucesso", f"Pasta '{nome_pasta}' criada com sucesso!")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao criar pasta:\n{e}")

def abrir_pasta():
    global root_path
    pasta = filedialog.askdirectory()
    if pasta:
        root_path = pasta
        montar_arvore(tree, root_path)
        limpar_selecao_e_editor()

def novo_arquivo():
    limpar_selecao_e_editor()

def abrir_arquivo():
    global arquivo_atual, current_language
    lang_config = get_current_language_config()
    default_ext = lang_config["extensions"][0] if lang_config["extensions"] else ".txt"
    
    filetypes = [(f"Arquivos {lang_config['name']}", f"*{default_ext}")]
    for lang_key, lang_conf in LANGUAGES.items():
        if lang_key != current_language:
            for ext in lang_conf["extensions"]:
                filetypes.append((f"Arquivos {lang_conf['name']}", f"*{ext}"))
    filetypes.append(("Todos os arquivos", "*.*"))
    
    caminho = filedialog.askopenfilename(filetypes=filetypes)
    if caminho:
        try:
            with open(caminho, "r", encoding="utf-8", errors="ignore") as f:
                conteudo = f.read()
            text_editor.config(state=NORMAL)
            text_editor.delete("1.0", END)
            text_editor.insert(END, conteudo)
            arquivo_atual = caminho
            
            # Detecta e muda a linguagem automaticamente
            nova_linguagem = detectar_linguagem_por_extensao(caminho)
            if nova_linguagem != current_language:
                mudar_linguagem(nova_linguagem)
                language_var.set(nova_linguagem)
            
            atualizar_titulo()
            aplicar_syntax_highlight()
            atualizar_status()
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao abrir arquivo:\n{e}")

def configurar_linguagem():
    """Abre janela de configuração para a linguagem atual"""
    lang_config = get_current_language_config()
    
    config_window = Toplevel(root)
    config_window.title(f"Configurar {lang_config['name']}")
    config_window.geometry("500x200")
    config_window.config(bg=themes[current_theme]["bg"])
    
    Label(config_window, text=f"Caminho do executável {lang_config['name']}:", 
          bg=themes[current_theme]["bg"], fg=themes[current_theme]["fg"]).pack(pady=10)
    
    path_var = StringVar(value=current_config["languages"].get(current_language, {}).get("path", ""))
    path_entry = Entry(config_window, textvariable=path_var, width=60,
                      bg=themes[current_theme]["entry_bg"], fg=themes[current_theme]["entry_fg"])
    path_entry.pack(pady=5)
    
    def procurar_executavel():
        caminho = filedialog.askopenfilename(
            title=f"Selecionar executável {lang_config['name']}",
            filetypes=[("Executáveis", "*.exe"), ("Todos os arquivos", "*.*")]
        )
        if caminho:
            path_var.set(caminho)
    
    Button(config_window, text="Procurar...", command=procurar_executavel,
           bg=themes[current_theme]["button_bg"], fg=themes[current_theme]["button_fg"]).pack(pady=5)
    
    def salvar_config():
        if current_language not in current_config["languages"]:
            current_config["languages"][current_language] = {}
        current_config["languages"][current_language]["path"] = path_var.get()
        salvar_configuracao()
        config_window.destroy()
        messagebox.showinfo("Sucesso", "Configuração salva!")
    
    Button(config_window, text="Salvar", command=salvar_config,
           bg=themes[current_theme]["button_bg"], fg=themes[current_theme]["button_fg"]).pack(pady=10)

# Criação da interface principal
root = Tk()
root.title("Multi-Language IDE 🚀")
root.geometry("1400x900")

# Carrega configurações
carregar_configuracao()

# Menu principal
menubar = Menu(root)
root.config(menu=menubar)

# Menu Arquivo
file_menu = Menu(menubar, tearoff=0)
menubar.add_cascade(label="Arquivo", menu=file_menu)
file_menu.add_command(label="Novo", command=novo_arquivo, accelerator="Ctrl+N")
file_menu.add_command(label="Abrir", command=abrir_arquivo, accelerator="Ctrl+O")
file_menu.add_command(label="Salvar", command=salvar_arquivo, accelerator="Ctrl+S")
file_menu.add_command(label="Salvar Como", command=salvar_como, accelerator="Ctrl+Shift+S")
file_menu.add_separator()
file_menu.add_command(label="Abrir Pasta", command=abrir_pasta)
file_menu.add_separator()
file_menu.add_command(label="Sair", command=root.quit)

# Menu Editar
edit_menu = Menu(menubar, tearoff=0)
menubar.add_cascade(label="Editar", menu=edit_menu)
edit_menu.add_command(label="Criar Arquivo", command=criar_arquivo)
edit_menu.add_command(label="Criar Pasta", command=criar_pasta)
edit_menu.add_command(label="Excluir", command=excluir_item)

# Menu Executar
run_menu = Menu(menubar, tearoff=0)
menubar.add_cascade(label="Executar", menu=run_menu)
run_menu.add_command(label="Executar Código", command=run_code, accelerator="F5")
run_menu.add_separator()
run_menu.add_command(label="Iniciar Terminal", command=start_terminal)
run_menu.add_command(label="Parar Terminal", command=stop_terminal)

# Menu Linguagem
language_menu = Menu(menubar, tearoff=0)
menubar.add_cascade(label="Linguagem", menu=language_menu)

language_var = StringVar(value=current_language)
for lang_key, lang_config in LANGUAGES.items():
    language_menu.add_radiobutton(
        label=f"{lang_config['icon']} {lang_config['name']}", 
        variable=language_var, 
        value=lang_key,
        command=lambda l=lang_key: mudar_linguagem(l)
    )
language_menu.add_separator()
language_menu.add_command(label="Configurar Linguagem Atual", command=configurar_linguagem)

# Menu Tema
theme_menu = Menu(menubar, tearoff=0)
menubar.add_cascade(label="Tema", menu=theme_menu)
for tema in themes.keys():
    theme_menu.add_command(label=tema.title(), command=lambda t=tema: mudar_tema(t))

# Frame principal
main_frame = Frame(root)
main_frame.pack(fill=BOTH, expand=True)

# Frame esquerdo (árvore de arquivos)
frame_tree = Frame(main_frame, width=300)
frame_tree.pack(side=LEFT, fill=Y)
frame_tree.pack_propagate(False)

Label(frame_tree, text="Explorador de Arquivos", font=("Segoe UI", 12, "bold")).pack(pady=5)

tree = ttk.Treeview(frame_tree)
tree.pack(fill=BOTH, expand=True, padx=5, pady=5)
tree.bind("<Double-1>", ao_clicar)

# Frame direito
right_frame = Frame(main_frame)
right_frame.pack(side=RIGHT, fill=BOTH, expand=True)

# Notebook para abas
notebook = ttk.Notebook(right_frame)
notebook.pack(fill=BOTH, expand=True, padx=5, pady=5)

# Aba do Editor
editor_frame = Frame(notebook)
notebook.add(editor_frame, text="Editor")

# Barra de ferramentas
toolbar = Frame(editor_frame)
toolbar.pack(fill=X, padx=5, pady=5)

run_button = Button(toolbar, text="▶ Executar (F5)", command=run_code)
run_button.pack(side=LEFT, padx=5)

# Seletor de linguagem na toolbar
Label(toolbar, text="Linguagem:").pack(side=LEFT, padx=(20, 5))
language_combo = ttk.Combobox(toolbar, textvariable=language_var, 
                             values=[f"{config['icon']} {config['name']}" for config in LANGUAGES.values()],
                             state="readonly", width=20)
language_combo.pack(side=LEFT, padx=5)

def on_language_change(event):
    selected = language_combo.get()
    for lang_key, lang_config in LANGUAGES.items():
        if f"{lang_config['icon']} {lang_config['name']}" == selected:
            mudar_linguagem(lang_key)
            break

language_combo.bind("<<ComboboxSelected>>", on_language_change)

# Editor de texto
text_editor = Text(editor_frame, wrap=NONE, undo=True)
text_editor.pack(fill=BOTH, expand=True, padx=5, pady=5)

# Scrollbars para o editor
scrollbar_y = Scrollbar(text_editor, orient=VERTICAL, command=text_editor.yview)
scrollbar_y.pack(side=RIGHT, fill=Y)
text_editor.config(yscrollcommand=scrollbar_y.set)

scrollbar_x = Scrollbar(editor_frame, orient=HORIZONTAL, command=text_editor.xview)
scrollbar_x.pack(side=BOTTOM, fill=X)
text_editor.config(xscrollcommand=scrollbar_x.set)

# Aba de Saída
output_frame = Frame(notebook)
notebook.add(output_frame, text="Saída")

output_box = Text(output_frame, state=DISABLED, wrap=WORD)
output_box.pack(fill=BOTH, expand=True, padx=5, pady=5)

# Aba do Terminal
terminal_frame = Frame(notebook)
notebook.add(terminal_frame, text="Terminal")

Label(terminal_frame, text="Terminal Interativo", font=("Segoe UI", 12, "bold")).pack(pady=5)

terminal_input_frame = Frame(terminal_frame)
terminal_input_frame.pack(fill=X, padx=5, pady=5)

Label(terminal_input_frame, text=">>>").pack(side=LEFT)
terminal_entry = Entry(terminal_input_frame)
terminal_entry.pack(side=LEFT, fill=X, expand=True, padx=5)

terminal_run_button = Button(terminal_input_frame, text="Enviar Comando", command=send_terminal_command)
terminal_run_button.pack(side=RIGHT)

# Aba de Configurações
config_frame = Frame(notebook)
notebook.add(config_frame, text="Configurações")

Label(config_frame, text="Configurações do IDE", font=("Segoe UI", 14, "bold")).pack(pady=10)

# Configurações de tema
theme_config_frame = Frame(config_frame)
theme_config_frame.pack(fill=X, padx=20, pady=10)

Label(theme_config_frame, text="Tema:", font=("Segoe UI", 10, "bold")).pack(side=LEFT)
for tema in themes.keys():
    Button(theme_config_frame, text=tema.title(), 
           command=lambda t=tema: mudar_tema(t)).pack(side=LEFT, padx=5)

# Configurações de fonte
font_config_frame = Frame(config_frame)
font_config_frame.pack(fill=X, padx=20, pady=10)

Label(font_config_frame, text="Tamanho da Fonte:", font=("Segoe UI", 10, "bold")).pack(side=LEFT)

def mudar_tamanho_fonte(delta):
    current_config["editor"]["font_size"] += delta
    if current_config["editor"]["font_size"] < 8:
        current_config["editor"]["font_size"] = 8
    elif current_config["editor"]["font_size"] > 24:
        current_config["editor"]["font_size"] = 24
    aplicar_tema()
    salvar_configuracao()

Button(font_config_frame, text="-", command=lambda: mudar_tamanho_fonte(-1)).pack(side=LEFT, padx=5)
font_size_label = Label(font_config_frame, text=str(current_config["editor"]["font_size"]))
font_size_label.pack(side=LEFT, padx=5)
Button(font_config_frame, text="+", command=lambda: mudar_tamanho_fonte(1)).pack(side=LEFT, padx=5)

# Barra de status
status_frame = Frame(root)
status_frame.pack(fill=X, side=BOTTOM)

status_label = Label(status_frame, text="Pronto", anchor=W)
status_label.pack(fill=X, padx=5, pady=2)

# Eventos de teclado
text_editor.bind("<KeyRelease>", on_key_release)
text_editor.bind("<Key>", global_key_handler)
terminal_entry.bind("<Return>", send_terminal_command)

# Atalhos de teclado
root.bind("<Control-n>", lambda e: novo_arquivo())
root.bind("<Control-o>", lambda e: abrir_arquivo())
root.bind("<Control-s>", lambda e: salvar_arquivo())
root.bind("<Control-Shift-S>", lambda e: salvar_como())
root.bind("<F5>", lambda e: run_code())

# Aplica tema inicial
aplicar_tema()
atualizar_titulo()
atualizar_status()

# Atualiza o label do tamanho da fonte
def atualizar_font_label():
    font_size_label.config(text=str(current_config["editor"]["font_size"]))
    root.after(100, atualizar_font_label)

atualizar_font_label()

# Inicia a aplicação
if __name__ == "__main__":
    root.mainloop()
    salvar_configuracao()

