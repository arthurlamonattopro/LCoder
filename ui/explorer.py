import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QLabel, QMessageBox, QTreeWidget, QTreeWidgetItem, QVBoxLayout

from core.languages import LANGUAGES


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}


class Explorer(QTreeWidget):
    def __init__(self, config_manager, open_file_callback=None, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.open_file_callback = open_file_callback
        self.root_path = None

        self.setHeaderHidden(True)
        self.itemExpanded.connect(self.on_item_expanded)
        self.itemDoubleClicked.connect(self.on_item_double_clicked)

    def set_root_path(self, path):
        self.root_path = path
        self.refresh()

    def refresh(self):
        self.clear()
        if not self.root_path:
            return
        self._populate_children(None, self.root_path)

    def _sorted_items(self, path):
        try:
            items = os.listdir(path)
        except (PermissionError, FileNotFoundError, OSError):
            return []
        return sorted(items, key=lambda x: (not os.path.isdir(os.path.join(path, x)), x.lower()))

    def _icon_for_file(self, file_path):
        ext = os.path.splitext(file_path)[1].lower()
        if ext in IMAGE_EXTENSIONS:
            return "🖼️"

        for lang_config in LANGUAGES.values():
            if ext in lang_config.get("extensions", []):
                return lang_config.get("icon", "📄")

        return "📄"

    def _populate_children(self, parent_item, path):
        for name in self._sorted_items(path):
            full_path = os.path.join(path, name)
            is_dir = os.path.isdir(full_path)
            icon = "📁" if is_dir else self._icon_for_file(full_path)

            item = QTreeWidgetItem([f" {icon}  {name}"])
            item.setData(0, Qt.UserRole, full_path)

            if parent_item is None:
                self.addTopLevelItem(item)
            else:
                parent_item.addChild(item)

            if is_dir:
                # Placeholder to draw expand indicator before loading directory content.
                placeholder = QTreeWidgetItem(["loading..."])
                placeholder.setData(0, Qt.UserRole, None)
                item.addChild(placeholder)

    def on_item_expanded(self, item):
        path = item.data(0, Qt.UserRole)
        if not path or not os.path.isdir(path):
            return

        if item.childCount() == 1 and item.child(0).data(0, Qt.UserRole) is None:
            item.takeChild(0)
            self._populate_children(item, path)

    def get_selected_path(self):
        selected = self.selectedItems()
        if not selected:
            return None
        return selected[0].data(0, Qt.UserRole)

    def on_item_double_clicked(self, item, _column):
        path = item.data(0, Qt.UserRole)
        if not path or not os.path.isfile(path):
            return

        ext = os.path.splitext(path)[1].lower()
        if ext in IMAGE_EXTENSIONS:
            self.abrir_imagem(path)
            return

        if callable(self.open_file_callback):
            self.open_file_callback(path)

    def abrir_imagem(self, caminho_imagem):
        try:
            pixmap = QPixmap(caminho_imagem)
            if pixmap.isNull():
                raise ValueError("Formato de imagem nao suportado.")

            dialog = QDialog(self)
            dialog.setWindowTitle(f"Visualizador - {os.path.basename(caminho_imagem)}")

            label = QLabel(dialog)
            label.setAlignment(Qt.AlignCenter)
            label.setPixmap(
                pixmap.scaled(800, 600, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )

            layout = QVBoxLayout(dialog)
            layout.addWidget(label)
            dialog.resize(840, 640)
            dialog.exec()
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Could not open image: {exc}")

    def apply_theme(self, theme):
        self.setStyleSheet(
            "QTreeWidget {"
            f"background-color: {theme['sidebar_bg']};"
            f"color: {theme['fg']};"
            "border: none;"
            "}"
            "QTreeWidget::item:selected {"
            f"background-color: {theme['select_bg']};"
            "}"
        )
