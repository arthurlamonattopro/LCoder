import os

from PySide6.QtCore import QEvent, Qt, QUrl
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
HTML_EXTENSIONS = {".html", ".htm"}
MARKDOWN_EXTENSIONS = {".md", ".markdown", ".mdx"}


def _read_text(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as handle:
        return handle.read()


class ImagePreviewWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = None
        self._fit = True

        self._label = QLabel("No image loaded.")
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setWordWrap(True)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setWidget(self._label)
        self._scroll.viewport().installEventFilter(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._scroll)

    def eventFilter(self, obj, event):
        if obj == self._scroll.viewport() and event.type() == QEvent.Resize:
            self._apply_pixmap()
        return super().eventFilter(obj, event)

    def set_fit(self, fit):
        self._fit = bool(fit)
        self._apply_pixmap()

    def set_message(self, message):
        self._pixmap = None
        self._label.setPixmap(QPixmap())
        self._label.setText(message)

    def set_image(self, path):
        if not path or not os.path.isfile(path):
            self.set_message("Select an image file to preview.")
            return
        pixmap = QPixmap(path)
        if pixmap.isNull():
            self.set_message("Unsupported image format.")
            return
        self._pixmap = pixmap
        self._apply_pixmap()

    def _apply_pixmap(self):
        if self._pixmap is None:
            return
        self._label.setText("")
        if self._fit:
            viewport = self._scroll.viewport().size()
            if viewport.width() <= 0 or viewport.height() <= 0:
                return
            scaled = self._pixmap.scaled(viewport, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self._label.setPixmap(scaled)
        else:
            self._label.setPixmap(self._pixmap)


class MediaPreviewDialog(QDialog):
    def __init__(self, context):
        super().__init__()
        self.context = context
        self._source_kind = None
        self._source_path = None
        self._source_text = None
        self._source_language = None
        self._source_editor = None

        self.setWindowTitle("Media Preview")
        self.resize(980, 720)

        self._build_ui()
        self._wire_events()

    def _build_ui(self):
        root = QVBoxLayout(self)

        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("Source path:"))
        self.path_entry = QLineEdit()
        self.path_entry.setPlaceholderText("Select a file or use the active editor")
        top_row.addWidget(self.path_entry)

        self.btn_browse = QPushButton("Browse")
        self.btn_use_editor = QPushButton("Use Active Editor")
        self.btn_reload = QPushButton("Reload")
        top_row.addWidget(self.btn_browse)
        top_row.addWidget(self.btn_use_editor)
        top_row.addWidget(self.btn_reload)
        root.addLayout(top_row)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs)

        self.image_tab = QWidget()
        image_layout = QVBoxLayout(self.image_tab)
        image_layout.setContentsMargins(8, 8, 8, 8)
        fit_row = QHBoxLayout()
        self.fit_checkbox = QCheckBox("Fit to window")
        self.fit_checkbox.setChecked(True)
        fit_row.addWidget(self.fit_checkbox)
        fit_row.addStretch(1)
        image_layout.addLayout(fit_row)
        self.image_preview = ImagePreviewWidget()
        image_layout.addWidget(self.image_preview)
        self.tabs.addTab(self.image_tab, "Image")

        self.html_tab = QWidget()
        html_layout = QVBoxLayout(self.html_tab)
        html_layout.setContentsMargins(8, 8, 8, 8)
        self.html_view = QTextBrowser()
        self.html_view.setOpenExternalLinks(True)
        html_layout.addWidget(self.html_view)
        self.tabs.addTab(self.html_tab, "HTML")

        self.markdown_tab = QWidget()
        markdown_layout = QVBoxLayout(self.markdown_tab)
        markdown_layout.setContentsMargins(8, 8, 8, 8)
        self.markdown_view = QTextBrowser()
        self.markdown_view.setOpenExternalLinks(True)
        markdown_layout.addWidget(self.markdown_view)
        self.tabs.addTab(self.markdown_tab, "Markdown")

        self._set_browser_message(self.html_view, "No HTML content to preview.")
        self._set_browser_message(self.markdown_view, "No Markdown content to preview.")

    def _wire_events(self):
        self.btn_browse.clicked.connect(self._browse_file)
        self.btn_use_editor.clicked.connect(self.load_from_active_editor)
        self.btn_reload.clicked.connect(self.refresh)
        self.path_entry.returnPressed.connect(self._load_from_path_entry)
        self.fit_checkbox.toggled.connect(self.image_preview.set_fit)

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open File")
        if path:
            self.load_from_path(path)

    def _load_from_path_entry(self):
        path = self.path_entry.text().strip()
        if path:
            self.load_from_path(path)

    def _try_get_active_path(self):
        if not self.context or not getattr(self.context, "window", None):
            return None
        window_api = self.context.window
        main_window = getattr(window_api, "_window", None)
        if not main_window:
            return None
        try:
            meta = main_window.get_current_tab_meta()
        except Exception:
            return None
        if not meta:
            return None
        return meta.get("path")

    def load_from_active_editor(self):
        if not self.context or not getattr(self.context, "window", None):
            QMessageBox.information(self, "Media Preview", "No active editor available.")
            return
        editor = self.context.window.active_editor()
        if not editor:
            QMessageBox.information(self, "Media Preview", "No active editor available.")
            return

        self._source_kind = "editor"
        self._source_editor = editor
        self._source_language = getattr(editor, "current_language", None)
        self._source_path = self._try_get_active_path()
        self._source_text = editor.toPlainText()
        self.path_entry.setText(self._source_path or "")
        self._render()

    def load_from_path(self, path):
        if not path:
            return
        self._source_kind = "file"
        self._source_editor = None
        self._source_language = None
        self._source_path = path
        self._source_text = None

        ext = os.path.splitext(path)[1].lower()
        if ext not in IMAGE_EXTENSIONS and os.path.isfile(path):
            self._source_text = _read_text(path)

        self.path_entry.setText(path)
        self._render()

    def refresh(self):
        if self._source_kind == "editor" and self._source_editor is not None:
            self._source_text = self._source_editor.toPlainText()
            self._source_language = getattr(self._source_editor, "current_language", None)
        elif self._source_kind == "file" and self._source_path:
            if not os.path.exists(self._source_path):
                QMessageBox.warning(self, "Media Preview", "File not found on disk.")
                return
            ext = os.path.splitext(self._source_path)[1].lower()
            if ext not in IMAGE_EXTENSIONS:
                self._source_text = _read_text(self._source_path)
            else:
                self._source_text = None
        else:
            QMessageBox.information(self, "Media Preview", "Nothing to refresh.")
            return

        self._render()

    def _detect_mode(self):
        path = self._source_path
        text = self._source_text or ""
        lang = (self._source_language or "").lower()
        ext = os.path.splitext(path)[1].lower() if path else ""

        if ext in IMAGE_EXTENSIONS:
            return "image"
        if ext in HTML_EXTENSIONS:
            return "html"
        if ext in MARKDOWN_EXTENSIONS:
            return "markdown"
        if lang == "html":
            return "html"
        if lang in ("markdown", "md"):
            return "markdown"
        lowered = text.lstrip().lower()
        if lowered.startswith("<!doctype html") or "<html" in lowered:
            return "html"
        if text:
            return "markdown"
        return None

    def _render(self):
        path = self._source_path
        text = self._source_text

        # Image tab
        if path and os.path.splitext(path)[1].lower() in IMAGE_EXTENSIONS:
            self.image_preview.set_image(path)
        else:
            self.image_preview.set_message("Select an image file to preview.")

        # HTML tab
        if text:
            self._set_html(text, path)
        else:
            self._set_browser_message(self.html_view, "No HTML content to preview.")

        # Markdown tab
        if text:
            self._set_markdown(text, path)
        else:
            self._set_browser_message(self.markdown_view, "No Markdown content to preview.")

        mode = self._detect_mode()
        if mode == "image":
            self.tabs.setCurrentWidget(self.image_tab)
        elif mode == "html":
            self.tabs.setCurrentWidget(self.html_tab)
        elif mode == "markdown":
            self.tabs.setCurrentWidget(self.markdown_tab)

    def _set_browser_message(self, browser, message):
        browser.setPlainText(message)

    def _set_html(self, html, path=None):
        if path:
            base_dir = os.path.dirname(path)
            if base_dir:
                self.html_view.document().setBaseUrl(QUrl.fromLocalFile(base_dir))
        else:
            self.html_view.document().setBaseUrl(QUrl())
        self.html_view.setHtml(html)

    def _set_markdown(self, markdown_text, path=None):
        if path:
            base_dir = os.path.dirname(path)
            if base_dir:
                self.markdown_view.document().setBaseUrl(QUrl.fromLocalFile(base_dir))
        else:
            self.markdown_view.document().setBaseUrl(QUrl())

        if hasattr(self.markdown_view, "setMarkdown"):
            try:
                self.markdown_view.setMarkdown(markdown_text)
                return
            except Exception:
                pass
        self.markdown_view.setPlainText(markdown_text)


_preview_dialog = None


def _get_dialog(context):
    global _preview_dialog
    if _preview_dialog is None or not isinstance(_preview_dialog, MediaPreviewDialog):
        _preview_dialog = MediaPreviewDialog(context)
    return _preview_dialog


def activate(context):
    def open_dialog():
        dialog = _get_dialog(context)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def preview_active():
        dialog = _get_dialog(context)
        dialog.load_from_active_editor()
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    context.commands.register_command(
        "mediaPreview.open",
        open_dialog,
        title="Media Preview: Open",
    )
    context.commands.register_command(
        "mediaPreview.previewActive",
        preview_active,
        title="Media Preview: Preview Active Editor",
    )
    context.log("[media-preview] Activated.\n")


def deactivate():
    global _preview_dialog
    _preview_dialog = None
    return None
