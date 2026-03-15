import re
from collections import Counter

from PySide6.QtCore import QRect, QSize, Qt, QStringListModel, QTimer
from PySide6.QtGui import QColor, QFont, QKeyEvent, QPainter, QSyntaxHighlighter, QTextCharFormat, QTextCursor, QTextFormat
from PySide6.QtWidgets import QCompleter, QPlainTextEdit, QTextEdit, QWidget

from core.languages import LANGUAGES
from core.themes import THEMES, UI_CONFIG


class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.code_editor = editor

    def sizeHint(self):
        return QSize(self.code_editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.code_editor.line_number_area_paint_event(event)


class CodeHighlighter(QSyntaxHighlighter):
    def __init__(self, document, language_config, theme):
        super().__init__(document)
        self.language_config = language_config
        self.theme = theme
        self._init_formats()

    def _init_formats(self):
        syntax = self.theme["syntax"]

        self.keyword_format = QTextCharFormat()
        self.keyword_format.setForeground(QColor(syntax["keyword"]))

        self.function_format = QTextCharFormat()
        self.function_format.setForeground(QColor(syntax["function"]))

        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor(syntax["comment"]))

        self.string_format = QTextCharFormat()
        self.string_format.setForeground(QColor(syntax["string"]))

        self.number_format = QTextCharFormat()
        self.number_format.setForeground(QColor(syntax["number"]))

    def set_config(self, language_config, theme):
        self.language_config = language_config
        self.theme = theme
        self._init_formats()

    def _apply_word_list(self, text, words, fmt):
        for word in words:
            for match in re.finditer(r"\\b" + re.escape(word) + r"\\b", text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)

    def highlightBlock(self, text):
        if not self.language_config:
            return

        self._apply_word_list(text, self.language_config.get("keywords", []), self.keyword_format)
        self._apply_word_list(text, self.language_config.get("functions", []), self.function_format)

        number_pattern = self.language_config.get("number_pattern")
        if number_pattern:
            for match in re.finditer(number_pattern, text):
                self.setFormat(match.start(), match.end() - match.start(), self.number_format)

        for quote in self.language_config.get("string_quotes", []):
            if quote in ["\"\"\"", "'''"]:
                continue
            pattern = re.escape(quote) + r".*?" + re.escape(quote)
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), match.end() - match.start(), self.string_format)

        comment_prefix = self.language_config.get("comment_prefix")
        if comment_prefix:
            if comment_prefix == "<!--":
                idx = text.find("<!--")
                if idx != -1:
                    self.setFormat(idx, len(text) - idx, self.comment_format)
            else:
                idx = text.find(comment_prefix)
                if idx != -1:
                    self.setFormat(idx, len(text) - idx, self.comment_format)


class Editor(QPlainTextEdit):
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.current_language = self.config_manager.get("current_language") or "python"
        self._snippets = {}
        self._doc_words = set()
        self._doc_word_counts = {}
        self._attr_map = {}
        self._recent_scores = {}
        self._recent_index = 0
        self._show_line_numbers = True
        self._autocomplete_enabled = True
        self._autocomplete_delay = 200
        self._intelicode_enabled = True
        self._max_suggestions = 60
        self._base_suggestions = []
        self._lang_keywords = set()
        self._lang_functions = set()

        font_cfg = self.config_manager.get("editor") or {}
        font_name = font_cfg.get("font_family") or UI_CONFIG["font_code"][0]
        font_size = int(font_cfg.get("font_size") or UI_CONFIG["font_code"][1])
        font = QFont(font_name, font_size)
        self.setFont(font)
        self.setTabStopDistance(4 * self.fontMetrics().horizontalAdvance(" "))
        self.setLineWrapMode(QPlainTextEdit.NoWrap)

        self._line_number_bg = QColor("#252526")
        self._line_number_fg = QColor("#8c8c8c")
        self._current_line_bg = QColor("#2a2d2e")
        self._bracket_bg = QColor("#264f78")

        self.line_number_area = LineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self._on_cursor_moved)
        self.textChanged.connect(self._on_text_changed)
        self.update_line_number_area_width(0)

        lang_config = self.get_current_language_config()
        theme = THEMES[self.config_manager.get("theme") or "dark"]
        self.highlighter = CodeHighlighter(self.document(), lang_config, theme)

        self.completer = QCompleter(self)
        self.completer.setWidget(self)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setCompletionMode(QCompleter.PopupCompletion)
        self.completer.activated.connect(self.insert_completion)
        self._completer_model = QStringListModel(self)
        self.completer.setModel(self._completer_model)
        self._completion_timer = QTimer(self)
        self._completion_timer.setSingleShot(True)
        self._completion_timer.timeout.connect(self._update_doc_words)
        self._apply_indent_settings()
        self.update_completer_model()

        self._extra_selections = []
        self.apply_editor_settings()
        self.aplicar_syntax_highlight()

    def get_current_language_config(self):
        return LANGUAGES.get(self.current_language, LANGUAGES.get("python"))

    def set_language(self, language):
        if language in LANGUAGES:
            self.current_language = language
            self._apply_indent_settings()
            self.update_completer_model()
            self.aplicar_syntax_highlight()

    def update_completer_model(self):
        lang = self.get_current_language_config() or {}
        self._snippets = lang.get("snippets", {}) or {}
        self._lang_keywords = set(lang.get("keywords", []))
        self._lang_functions = set(lang.get("functions", []))
        suggestions = set(self._lang_keywords | self._lang_functions)
        suggestions.update(self._snippets.keys())
        suggestions.update(self._doc_words)
        self._base_suggestions = sorted(suggestions)
        prefix = self.completer.completionPrefix() or ""
        if prefix:
            self._update_completions(prefix)
        else:
            self._completer_model.setStringList(self._base_suggestions)

    def _apply_indent_settings(self):
        lang = self.get_current_language_config() or {}
        indent = lang.get("indent", {}) or {}
        size = int(indent.get("size") or 4)
        use_tabs = bool(indent.get("use_tabs"))
        if use_tabs:
            self.setTabStopDistance(4 * self.fontMetrics().horizontalAdvance(" "))
        else:
            self.setTabStopDistance(size * self.fontMetrics().horizontalAdvance(" "))

    def _update_doc_words(self):
        text = self.toPlainText()
        words = re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", text)
        counts = Counter(words)
        word_set = set(counts.keys())
        attr_map = self._extract_attr_map(text)
        if word_set != self._doc_words or counts != self._doc_word_counts or attr_map != self._attr_map:
            self._doc_words = word_set
            self._doc_word_counts = counts
            self._attr_map = attr_map
            self.update_completer_model()

    def _extract_attr_map(self, text):
        attr_map = {}
        for base, attr in re.findall(r"\\b([A-Za-z_][A-Za-z0-9_]*)\\.([A-Za-z_][A-Za-z0-9_]*)", text):
            attr_map.setdefault(base, set()).add(attr)
        return attr_map

    def line_number_area_width(self):
        digits = len(str(max(1, self.blockCount())))
        return 12 + self.fontMetrics().horizontalAdvance("9") * digits

    def update_line_number_area_width(self, _):
        if self._show_line_numbers:
            self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)
        else:
            self.setViewportMargins(0, 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def line_number_area_paint_event(self, event):
        if not self._show_line_numbers:
            return
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), self._line_number_bg)

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(self._line_number_fg)
                painter.drawText(
                    0,
                    top,
                    self.line_number_area.width() - 4,
                    self.fontMetrics().height(),
                    Qt.AlignRight,
                    number,
                )

            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

    def apply_theme(self, theme):
        self._line_number_bg = QColor(theme["sidebar_bg"])
        self._line_number_fg = QColor(theme["fg"])
        self._current_line_bg = QColor(theme["entry_bg"])
        self._bracket_bg = QColor(theme["select_bg"])

        self.setStyleSheet(
            "QPlainTextEdit {"
            f"background-color: {theme['editor_bg']};"
            f"color: {theme['fg']};"
            f"selection-background-color: {theme['select_bg']};"
            "border: none;"
            "padding: 6px;"
            "}"
        )
        self.aplicar_syntax_highlight()
        self.line_number_area.update()

    def aplicar_syntax_highlight(self):
        theme_name = self.config_manager.get("theme") or "dark"
        theme = THEMES.get(theme_name, THEMES["dark"])
        self.highlighter.set_config(self.get_current_language_config(), theme)
        self.highlighter.rehighlight()
        self._refresh_extra_selections()

    def _on_text_changed(self):
        self._refresh_extra_selections()
        if self._autocomplete_enabled:
            if self._intelicode_enabled:
                self._capture_recent_word()
            self._completion_timer.start(self._autocomplete_delay)

    def _on_cursor_moved(self):
        self._refresh_extra_selections()

    def _refresh_extra_selections(self):
        selections = []

        current_line = QTextEdit.ExtraSelection()
        current_line.format.setBackground(self._current_line_bg)
        current_line.format.setProperty(QTextFormat.FullWidthSelection, True)
        current_line.cursor = self.textCursor()
        current_line.cursor.clearSelection()
        selections.append(current_line)

        for idx in self._match_bracket_indices():
            sel = QTextEdit.ExtraSelection()
            sel.format.setBackground(self._bracket_bg)
            sel.format.setFontUnderline(True)
            c = self.textCursor()
            c.setPosition(idx)
            c.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, 1)
            sel.cursor = c
            selections.append(sel)

        self._extra_selections = selections
        self.setExtraSelections(selections)

    def _match_bracket_indices(self):
        text = self.toPlainText()
        if not text:
            return []

        pos = self.textCursor().position()
        candidate_positions = []
        if pos > 0:
            candidate_positions.append(pos - 1)
        if pos < len(text):
            candidate_positions.append(pos)

        for idx in candidate_positions:
            ch = text[idx]
            if ch in "()[]{}":
                match = self._find_matching_bracket(text, idx)
                if match is not None:
                    return [idx, match]
        return []

    def _find_matching_bracket(self, text, index):
        pairs = {"(": ")", "[": "]", "{": "}", ")": "(", "]": "[", "}": "{"}
        openers = "([{"
        ch = text[index]
        target = pairs[ch]

        if ch in openers:
            step = 1
            stack = 1
            i = index + 1
            while i < len(text):
                curr = text[i]
                if curr == ch:
                    stack += 1
                elif curr == target:
                    stack -= 1
                    if stack == 0:
                        return i
                i += step
        else:
            step = -1
            stack = 1
            i = index - 1
            while i >= 0:
                curr = text[i]
                if curr == ch:
                    stack += 1
                elif curr == target:
                    stack -= 1
                    if stack == 0:
                        return i
                i += step
        return None

    def insert_completion(self, completion):
        cursor = self.textCursor()
        prefix = self.completer.completionPrefix()
        if prefix:
            cursor.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor, len(prefix))
            cursor.removeSelectedText()
        snippet = self._snippets.get(completion)
        if snippet:
            marker = "$0"
            insert_text = snippet
            marker_index = snippet.find(marker)
            if marker_index != -1:
                insert_text = snippet.replace(marker, "")
            cursor.insertText(insert_text)
            if marker_index != -1:
                cursor.setPosition(cursor.position() - (len(insert_text) - marker_index))
                self.setTextCursor(cursor)
            else:
                self.setTextCursor(cursor)
        else:
            cursor.insertText(completion)
            self.setTextCursor(cursor)

    def text_under_cursor(self):
        cursor = self.textCursor()
        cursor.select(QTextCursor.WordUnderCursor)
        return cursor.selectedText()

    def _completion_context(self):
        cursor = self.textCursor()
        block_text = cursor.block().text()
        pos = cursor.positionInBlock()
        left = block_text[:pos]
        match = re.search(r"([A-Za-z_][A-Za-z0-9_]*)\\.([A-Za-z_][A-Za-z0-9_]*)?$", left)
        if match:
            base = match.group(1)
            partial = match.group(2) or ""
            return partial, base
        return self.text_under_cursor(), None

    def _capture_recent_word(self):
        cursor = self.textCursor()
        cursor.select(QTextCursor.WordUnderCursor)
        word = cursor.selectedText()
        if not word or len(word) < 3:
            return
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", word):
            return
        self._recent_index += 1
        self._recent_scores[word] = self._recent_index
        if len(self._recent_scores) > 2000:
            cutoff = self._recent_index - 1500
            self._recent_scores = {w: i for w, i in self._recent_scores.items() if i >= cutoff}

    def _update_completions(self, prefix, base=None):
        if base and base in self._attr_map:
            candidates = sorted(self._attr_map.get(base, []))
            if not candidates:
                candidates = self._base_suggestions
        else:
            candidates = self._base_suggestions

        if prefix:
            matches = [c for c in candidates if c.lower().startswith(prefix.lower())]
            if not matches and self._intelicode_enabled:
                matches = [c for c in candidates if prefix.lower() in c.lower()]
        else:
            matches = candidates

        if self._intelicode_enabled:
            matches.sort(key=lambda w: (-self._score_completion(w, prefix, base), w.lower()))
        else:
            matches.sort(key=lambda w: w.lower())

        if self._max_suggestions and len(matches) > self._max_suggestions:
            matches = matches[: self._max_suggestions]
        self._completer_model.setStringList(matches)

    def _score_completion(self, word, prefix, base=None):
        score = 0.0
        if word in self._snippets:
            score += 6.0
        if word in self._lang_keywords:
            score += 2.0
        if word in self._lang_functions:
            score += 3.0
        freq = self._doc_word_counts.get(word, 0)
        score += min(freq, 6)
        recent = self._recent_scores.get(word)
        if recent:
            distance = max(0, self._recent_index - recent)
            score += max(0, 6 - (distance // 15))
        if prefix and word.lower().startswith(prefix.lower()):
            score += 2.0
            if word == prefix:
                score += 1.0
        if base and base in self._attr_map and word in self._attr_map.get(base, set()):
            score += 1.5
        score -= len(word) * 0.01
        return score

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            cursor = self.textCursor()
            block_text = cursor.block().text()[: cursor.positionInBlock()]
            indent_match = re.match(r"^\\s*", block_text)
            indent = indent_match.group(0) if indent_match else ""
            lang = self.get_current_language_config() or {}
            indent_cfg = lang.get("indent", {}) or {}
            size = int(indent_cfg.get("size") or 4)
            use_tabs = bool(indent_cfg.get("use_tabs"))
            indent_unit = "\t" if use_tabs else (" " * size)

            if block_text.rstrip().endswith(":") or block_text.rstrip().endswith("{"):
                indent += indent_unit
            super().keyPressEvent(event)
            super().insertPlainText(indent)
            return

        if self.completer.popup().isVisible() and event.key() in (
            Qt.Key_Enter,
            Qt.Key_Return,
            Qt.Key_Escape,
            Qt.Key_Tab,
            Qt.Key_Backtab,
        ):
            event.ignore()
            return

        super().keyPressEvent(event)

        if not self._autocomplete_enabled:
            return

        ctrl_or_shift = event.modifiers() & (Qt.ControlModifier | Qt.ShiftModifier)
        if ctrl_or_shift and not event.text():
            return

        prefix, base = self._completion_context()
        if len(prefix) < 1 and not (self._intelicode_enabled and base):
            self.completer.popup().hide()
            return

        if prefix != self.completer.completionPrefix():
            self.completer.setCompletionPrefix(prefix)
        self._update_completions(prefix, base)
        self.completer.popup().setCurrentIndex(self.completer.completionModel().index(0, 0))

        rect = self.cursorRect()
        rect.setWidth(
            self.completer.popup().sizeHintForColumn(0)
            + self.completer.popup().verticalScrollBar().sizeHint().width()
        )
        self.completer.complete(rect)

    def cursor_position(self):
        cursor = self.textCursor()
        return cursor.blockNumber() + 1, cursor.columnNumber() + 1

    def apply_editor_settings(self):
        editor_cfg = self.config_manager.get("editor") or {}
        font_name = editor_cfg.get("font_family") or UI_CONFIG["font_code"][0]
        font_size = int(editor_cfg.get("font_size") or UI_CONFIG["font_code"][1])
        font = QFont(font_name, font_size)
        self.setFont(font)

        show_line_numbers = editor_cfg.get("show_line_numbers")
        if show_line_numbers is None:
            show_line_numbers = True
        self._show_line_numbers = bool(show_line_numbers)
        self.line_number_area.setVisible(self._show_line_numbers)
        self.update_line_number_area_width(0)

        word_wrap = editor_cfg.get("word_wrap")
        if word_wrap:
            self.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        else:
            self.setLineWrapMode(QPlainTextEdit.NoWrap)

        auto_cfg = self.config_manager.get("autocomplete") or {}
        self._autocomplete_enabled = bool(auto_cfg.get("enabled", True))
        self._autocomplete_delay = int(auto_cfg.get("delay") or 200)
        if not self._autocomplete_enabled:
            self.completer.popup().hide()

        intelicode_cfg = self.config_manager.get("intelicode") or {}
        self._intelicode_enabled = bool(intelicode_cfg.get("enabled", True))
        self._max_suggestions = int(intelicode_cfg.get("max_suggestions") or 60)
        self.update_completer_model()
