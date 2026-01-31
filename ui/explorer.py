import os
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
from core.languages import LANGUAGES
from core.themes import THEMES

class Explorer(ttk.Treeview):
    def __init__(self, master, config_manager, **kwargs):
        super().__init__(master, show="tree", **kwargs)
        self.config_manager = config_manager
        self.root_path = None
        self.bind("<Double-1>", self.on_double_click)

    def set_root_path(self, path):
        self.root_path = path
        self.refresh()

    def refresh(self):
        if self.root_path:
            self.montar_arvore(self.root_path)

    def montar_arvore(self, caminho, pai=""):
        for child in self.get_children(pai):
            self.delete(child)
        try:
            itens = sorted(os.listdir(caminho), key=lambda x: (not os.path.isdir(os.path.join(caminho, x)), x.lower()))
        except PermissionError:
            return
        for item in itens:
            caminho_completo = os.path.join(caminho, item)
            if os.path.isdir(caminho_completo):
                icon = "📁"
            else:
                ext = os.path.splitext(item)[1].lower()
                icon = "📄"
                for lang_config in LANGUAGES.values():
                    if ext in lang_config["extensions"]:
                        icon = lang_config["icon"]
                        break
                if ext in ['.txt', '.md']:
                    icon = "📄"
                elif ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp']:
                    icon = "🖼️"
            
            node = self.insert(pai, "end", text=f" {icon}  {item}", open=False)
            if os.path.isdir(caminho_completo):
                # Placeholder to allow expansion
                self.insert(node, "end", text="loading...")
        
        self.bind("<<TreeviewOpen>>", self.on_open)

    def on_open(self, event):
        item_id = self.focus()
        path = self.caminho_do_item(item_id)
        
        # Remove placeholder
        for child in self.get_children(item_id):
            self.delete(child)
            
        try:
            itens = sorted(os.listdir(path), key=lambda x: (not os.path.isdir(os.path.join(path, x)), x.lower()))
            for item in itens:
                caminho_completo = os.path.join(path, item)
                if os.path.isdir(caminho_completo):
                    icon = "📁"
                else:
                    ext = os.path.splitext(item)[1].lower()
                    icon = "📄"
                    for lang_config in LANGUAGES.values():
                        if ext in lang_config["extensions"]:
                            icon = lang_config["icon"]
                            break
                
                node = self.insert(item_id, "end", text=f" {icon}  {item}", open=False)
                if os.path.isdir(caminho_completo):
                    self.insert(node, "end", text="loading...")
        except:
            pass

    def get_selected_path(self):
        selecionados = self.selection()
        if not selecionados:
            return None
        return self.caminho_do_item(selecionados[0])

    def caminho_do_item(self, item_id):
        partes = []
        curr = item_id
        while curr:
            texto = self.item(curr, "text").strip()
            # Remove o ícone (assume que o ícone é o primeiro caractere ou parte do texto)
            # Nosso formato é " 📁  nome"
            if "  " in texto:
                nome = texto.split("  ", 1)[1]
            else:
                nome = texto
            partes.insert(0, nome)
            curr = self.parent(curr)
        return os.path.join(self.root_path, *partes)

    def on_double_click(self, event):
        path = self.get_selected_path()
        if path and os.path.isfile(path):
            ext = os.path.splitext(path)[1].lower()
            if ext in [".png", ".jpg", ".jpeg", ".gif", ".bmp"]:
                self.abrir_imagem(path)
            else:
                # master (explorer_container) -> sidebar_frame -> main_window
                main_window = self.master.master.master
                if hasattr(main_window, 'abrir_arquivo_por_caminho'):
                    main_window.abrir_arquivo_por_caminho(path)

    def abrir_imagem(self, caminho_imagem):
        try:
            theme_name = self.config_manager.get("theme")
            theme = THEMES[theme_name]
            
            img_window = tk.Toplevel(self)
            img_window.title(f"Visualizador - {os.path.basename(caminho_imagem)}")
            img_window.config(bg=theme["bg"])
            
            img = Image.open(caminho_imagem)
            max_size = (800, 600)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            img_tk = ImageTk.PhotoImage(img)
            
            label = tk.Label(img_window, image=img_tk, bg=theme["bg"])
            label.image = img_tk
            label.pack(padx=20, pady=20)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open image: {e}")
