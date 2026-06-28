"""Tests for core.languages helpers."""

from core.languages import (
    LANGUAGES,
    abrir_no_navegador,
    detectar_linguagem_por_extensao,
    encontrar_executavel,
)


def test_detect_python_extension():
    assert detectar_linguagem_por_extensao("foo.py") == "python"
    assert detectar_linguagem_por_extensao("/path/to/bar.PY") == "python"


def test_detect_javascript_extension():
    assert detectar_linguagem_por_extensao("app.js") == "javascript"


def test_detect_lua_extension():
    assert detectar_linguagem_por_extensao("script.lua") == "lua"


def test_detect_cpp_extensions():
    assert detectar_linguagem_por_extensao("main.cpp") == "cpp"
    assert detectar_linguagem_por_extensao("header.hpp") == "cpp"
    assert detectar_linguagem_por_extensao("legacy.c") == "cpp"
    assert detectar_linguagem_por_extensao("header.h") == "cpp"


def test_detect_html_extensions():
    assert detectar_linguagem_por_extensao("index.html") == "html"
    assert detectar_linguagem_por_extensao("index.htm") == "html"


def test_detect_unknown_extension_returns_none():
    assert detectar_linguagem_por_extensao("readme.md") is None
    assert detectar_linguagem_por_extensao("data.json") is None
    assert detectar_linguagem_por_extensao("noext") is None


def test_encontrar_executavel_webbrowser_returns_sentinel():
    """The HTML 'executable' is a sentinel value that should bypass PATH lookup."""
    assert encontrar_executavel("webbrowser") == "webbrowser"


def test_encontrar_executavel_falls_back_to_name():
    """For a non-existent command, encontrar_executavel should return the name itself."""
    result = encontrar_executavel("definitely-not-a-real-binary-xyz123")
    assert result == "definitely-not-a-real-binary-xyz123"


def test_all_languages_have_required_fields():
    """Every language definition must have the keys the editor relies on."""
    required_keys = {
        "name", "extensions", "icon", "executable",
        "run_args", "repl_args", "indent",
        "keywords", "functions", "comment_prefix",
        "string_quotes", "number_pattern",
    }
    # Skip extensions contributed at runtime via the ExtensionManager tests.
    builtin_langs = {"lua", "python", "javascript", "ruby", "php", "perl", "cpp", "html"}
    for lang_id in builtin_langs:
        cfg = LANGUAGES[lang_id]
        missing = required_keys - set(cfg.keys())
        assert not missing, f"Language '{lang_id}' is missing keys: {missing}"


def test_html_runs_in_browser(tmp_path):
    """HTML files should be openable in the default browser via abrir_no_navegador."""
    html_file = tmp_path / "test.html"
    html_file.write_text("<h1>hi</h1>")
    # We can't assert that the browser actually opened, but the function
    # should accept a valid path without raising.
    result = abrir_no_navegador(str(html_file))
    # On headless CI the browser may fail to launch — accept either outcome,
    # but it must not raise.
    assert result in (True, False)
