import ast
import importlib.util
import os
import sys


SKIP_IMPORT_BASES = {"self", "cls", "this"}


def auto_import_python(source, file_path=None, workspace_root=None):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source, []

    visitor = _ImportVisitor()
    visitor.visit(tree)

    search_paths = []
    if file_path:
        search_paths.append(os.path.dirname(os.path.abspath(file_path)))
    if workspace_root:
        search_paths.append(os.path.abspath(workspace_root))

    missing = []
    for name in sorted(visitor.attr_bases):
        if name in SKIP_IMPORT_BASES:
            continue
        if name in visitor.imported_names:
            continue
        if name in visitor.defined_names:
            continue
        if name in visitor.builtin_names:
            continue
        if _module_exists(name, search_paths):
            missing.append(name)

    if not missing:
        return source, []

    new_source = _insert_imports(source, missing, tree)
    return new_source, missing


class _ImportVisitor(ast.NodeVisitor):
    def __init__(self):
        self.imported_names = set()
        self.defined_names = set()
        self.attr_bases = set()
        self.builtin_names = set(dir(__builtins__))

    def visit_Import(self, node):
        for alias in node.names:
            name = alias.asname or alias.name.split(".")[0]
            self.imported_names.add(name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        for alias in node.names:
            if alias.name == "*":
                continue
            name = alias.asname or alias.name
            self.imported_names.add(name)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        self.defined_names.add(node.name)
        self._add_args(node.args)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        self.defined_names.add(node.name)
        self._add_args(node.args)
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        self.defined_names.add(node.name)
        self.generic_visit(node)

    def visit_Assign(self, node):
        for target in node.targets:
            self._collect_target(target)
        self.generic_visit(node)

    def visit_AnnAssign(self, node):
        self._collect_target(node.target)
        self.generic_visit(node)

    def visit_AugAssign(self, node):
        self._collect_target(node.target)
        self.generic_visit(node)

    def visit_For(self, node):
        self._collect_target(node.target)
        self.generic_visit(node)

    def visit_AsyncFor(self, node):
        self._collect_target(node.target)
        self.generic_visit(node)

    def visit_With(self, node):
        for item in node.items:
            if item.optional_vars is not None:
                self._collect_target(item.optional_vars)
        self.generic_visit(node)

    def visit_AsyncWith(self, node):
        for item in node.items:
            if item.optional_vars is not None:
                self._collect_target(item.optional_vars)
        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        if node.name:
            self.defined_names.add(node.name)
        self.generic_visit(node)

    def visit_comprehension(self, node):
        self._collect_target(node.target)
        self.generic_visit(node)

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Store):
            self.defined_names.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node):
        if isinstance(node.value, ast.Name):
            self.attr_bases.add(node.value.id)
        self.generic_visit(node)

    def _collect_target(self, target):
        if isinstance(target, ast.Name):
            self.defined_names.add(target.id)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                self._collect_target(elt)

    def _add_args(self, args):
        for arg in args.posonlyargs:
            self.defined_names.add(arg.arg)
        for arg in args.args:
            self.defined_names.add(arg.arg)
        for arg in args.kwonlyargs:
            self.defined_names.add(arg.arg)
        if args.vararg:
            self.defined_names.add(args.vararg.arg)
        if args.kwarg:
            self.defined_names.add(args.kwarg.arg)


def _module_exists(name, search_paths):
    if name in sys.builtin_module_names:
        return True
    try:
        if importlib.util.find_spec(name) is not None:
            return True
    except (ImportError, ValueError):
        pass

    for base in search_paths:
        if not base:
            continue
        candidate = os.path.join(base, f"{name}.py")
        if os.path.isfile(candidate):
            return True
        pkg_init = os.path.join(base, name, "__init__.py")
        if os.path.isfile(pkg_init):
            return True

    return False


def _insert_imports(source, missing, tree):
    lines = source.splitlines()
    insert_at = _find_insertion_line(lines, tree)
    import_lines = [f"import {name}" for name in missing]

    before_blank = insert_at > 0 and lines[insert_at - 1].strip() != ""
    after_blank = insert_at < len(lines) and lines[insert_at].strip() != ""

    new_lines = []
    new_lines.extend(lines[:insert_at])
    if before_blank:
        new_lines.append("")
    new_lines.extend(import_lines)
    if after_blank:
        new_lines.append("")
    new_lines.extend(lines[insert_at:])

    return "\n".join(new_lines) + ("\n" if source.endswith("\n") else "")


def _find_insertion_line(lines, tree):
    idx = 0
    if lines and lines[0].startswith("#!"):
        idx = 1
    if idx < len(lines) and _is_encoding_line(lines[idx]):
        idx += 1

    doc_node = None
    if tree.body:
        first = tree.body[0]
        if isinstance(first, ast.Expr) and isinstance(getattr(first, "value", None), ast.Constant):
            if isinstance(first.value.value, str):
                doc_node = first
    if doc_node and getattr(doc_node, "end_lineno", None):
        idx = max(idx, int(doc_node.end_lineno))

    for node in tree.body:
        if node is doc_node:
            continue
        if isinstance(node, ast.ImportFrom) and node.module == "__future__":
            if getattr(node, "end_lineno", None):
                idx = max(idx, int(node.end_lineno))
            continue
        break

    insert_at = idx
    found_import = False
    i = idx
    while i < len(lines):
        stripped = lines[i].strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue
        if stripped.startswith("import ") or stripped.startswith("from "):
            found_import = True
            i += 1
            continue
        break

    if found_import:
        insert_at = i

    return insert_at


def _is_encoding_line(line):
    text = line.strip().lower()
    if not text.startswith("#"):
        return False
    return "coding" in text
