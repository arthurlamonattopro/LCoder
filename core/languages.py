import os
import subprocess

LANGUAGES = {
    "lua": {
        "name": "Lua",
        "extensions": [".lua"],
        "icon": "🌙",
        "executable": "lua",
        "run_args": ["{file}"],
        "repl_args": ["-e", "{code}"],
        "indent": {"size": 4, "use_tabs": False},
        "snippets": {
            "func": "function name()\n    $0\nend",
            "fori": "for i = 1, N do\n    $0\nend",
        },
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
        "executable": "python",
        "run_args": ["{file}"],
        "repl_args": ["-c", "{code}"],
        "indent": {"size": 4, "use_tabs": False},
        "snippets": {
            "ifmain": "if __name__ == \"__main__\":\n    $0",
            "def": "def name(args):\n    $0",
        },
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
        "indent": {"size": 2, "use_tabs": False},
        "snippets": {
            "cl": "console.log($0);",
            "func": "function name() {\n  $0\n}",
        },
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
        "indent": {"size": 2, "use_tabs": False},
        "snippets": {
            "def": "def name\n  $0\nend",
            "class": "class Name\n  $0\nend",
        },
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
        "indent": {"size": 4, "use_tabs": False},
        "snippets": {
            "echo": "echo \"$0\";",
            "func": "function name($args) {\n    $0\n}",
        },
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
        "indent": {"size": 4, "use_tabs": False},
        "snippets": {
            "sub": "sub name {\n    $0\n}",
            "if": "if ($cond) {\n    $0\n}",
        },
        "keywords": ["sub", "if", "elsif", "else", "unless", "for", "foreach", "while", "until", "do", "given", "when", "default", "return", "last", "next", "redo", "retry", "super", "self", "true", "false", "nil", "and", "or", "not"],
        "functions": ["print", "say", "printf", "sprintf", "chomp", "chop", "length", "substr", "index", "rindex", "split", "join", "grep", "map", "sort", "reverse", "push", "pop", "shift", "unshift", "splice"],
        "comment_prefix": "#",
        "string_quotes": ["\"", "\'"],
        "number_pattern": r'\b\d+(\.\d+)?\b'
    },
    "cpp": {
        "name": "C++",
        "extensions": [".cpp", ".hpp", ".c", ".h"],
        "icon": "⚙️",
        "executable": "g++",
        "run_args": ["{file}"],
        "indent": {"size": 4, "use_tabs": False},
        "snippets": {
            "main": "int main() {\n    $0\n    return 0;\n}",
            "cout": "std::cout << $0 << std::endl;",
        },
        "keywords": ["int", "float", "double", "char", "void", "if", "else", "for", "while", "do", "switch", "case", "default", "break", "continue", "return", "class", "struct", "public", "private", "protected", "namespace", "using", "include", "new", "delete", "try", "catch", "throw", "true", "false"],
        "functions": ["main", "printf", "scanf", "cout", "cin", "endl", "vector", "string", "map", "set", "push_back", "size", "begin", "end"],
        "comment_prefix": "//",
        "string_quotes": ["\"", "\'"],
        "number_pattern": r'\b\d+(\.\d+)?\b'
    },
    "html": {
        "name": "HTML",
        "extensions": [".html", ".htm"],
        "icon": "🌐",
        "executable": "firefox",
        "run_args": ["{file}"],
        "repl_args": [],
        "indent": {"size": 2, "use_tabs": False},
        "snippets": {
            "html5": "<!DOCTYPE html>\n<html>\n  <head>\n    <meta charset=\"utf-8\" />\n    <title>$0</title>\n  </head>\n  <body>\n  </body>\n</html>",
            "link": "<a href=\"$0\">link</a>",
        },
        "keywords": ["html", "head", "title", "body", "div", "span", "h1", "h2", "h3", "h4", "h5", "h6", "p", "a", "img", "ul", "ol", "li", "table", "tr", "td", "th", "form", "input", "button", "script", "style", "link", "meta"],
        "functions": ["id", "class", "href", "src", "alt", "style", "type", "value", "name", "target", "rel", "charset"],
        "comment_prefix": "<!--",
        "string_quotes": ["\"", "\'"],
        "number_pattern": r'\b\d+(\.\d+)?\b'
    }
}

def encontrar_executavel(nome):
    """Encontra o executavel de uma linguagem no sistema"""
    try:
        if os.name == "nt":
            result = subprocess.run(["where", nome], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.splitlines()[0].strip()
        else:
            result = subprocess.run(["which", nome], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
    except:
        pass

    if nome == "python":
        try:
            result = subprocess.run(["python3", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                return "python3"
        except:
            pass

    if os.name == 'nt':
        common_paths = [
            rf"C:\Program Files\{nome}\{nome}.exe",
            rf"C:\{nome}\{nome}.exe",
            f"{nome}.exe",
        ]
        for path in common_paths:
            if os.path.exists(path):
                return path

    return nome

def detectar_linguagem_por_extensao(caminho_arquivo):
    """Detecta a linguagem baseada na extensão do arquivo"""
    ext = os.path.splitext(caminho_arquivo)[1].lower()
    for lang_key, lang_config in LANGUAGES.items():
        if ext in lang_config["extensions"]:
            return lang_key
    return None
