"""Tests for utils.auto_importer."""
import textwrap

from utils.auto_importer import auto_import_python


def test_no_missing_imports_returns_unchanged():
    source = "import os\n\nprint(os.getcwd())\n"
    new_source, missing = auto_import_python(source)
    assert missing == []
    assert new_source == source


def test_inserts_missing_stdlib_import():
    source = "value = json.loads('{}')\n"
    new_source, missing = auto_import_python(source)
    assert "json" in missing
    assert "import json" in new_source
    # Original code is preserved
    assert "value = json.loads('{}')" in new_source


def test_does_not_reimport_already_imported():
    source = "import json\n\nvalue = json.loads('{}')\n"
    new_source, missing = auto_import_python(source)
    assert missing == []
    # No duplicate import line is added
    assert new_source.count("import json") == 1


def test_skips_self_and_cls():
    source = textwrap.dedent(
        """
        class Foo:
            def bar(self):
                return self.baz()
        """
    ).strip() + "\n"
    new_source, missing = auto_import_python(source)
    assert missing == []
    assert "import self" not in new_source
    assert "import cls" not in new_source


def test_skips_defined_names():
    source = textwrap.dedent(
        """
        def my_func():
            return my_func.helper()
        """
    ).strip() + "\n"
    new_source, missing = auto_import_python(source)
    assert missing == []
    assert "import my_func" not in new_source


def test_invalid_syntax_returns_original():
    source = "def broken(:\n"
    new_source, missing = auto_import_python(source)
    assert missing == []
    assert new_source == source


def test_insertion_after_module_docstring():
    source = textwrap.dedent(
        '''
        """Module docstring."""
        value = sys.maxsize
        '''
    ).strip() + "\n"
    new_source, missing = auto_import_python(source)
    assert "sys" in missing
    # The docstring stays at the top
    assert new_source.startswith('"""Module docstring."""')
    # The import appears after the docstring
    docstring_end = new_source.index('"""Module docstring."""') + len('"""Module docstring."""')
    import_pos = new_source.index("import sys")
    assert import_pos > docstring_end


def test_inserts_local_module(tmp_path):
    # Create a local module file in the same directory
    (tmp_path / "mymod.py").write_text("def hello():\n    return 'hi'\n")
    source = "result = mymod.hello()\n"
    new_source, missing = auto_import_python(
        source, file_path=str(tmp_path / "main.py"), workspace_root=str(tmp_path)
    )
    assert "mymod" in missing
    assert "import mymod" in new_source


def test_skips_builtin_names():
    # ``len`` is a builtin, so no import should be added.
    source = "n = len([1, 2, 3])\n"
    new_source, missing = auto_import_python(source)
    assert missing == []
    assert "import len" not in new_source


def test_preserves_existing_imports_order():
    source = textwrap.dedent(
        """
        import os

        value = json.loads('{}')
        """
    ).strip() + "\n"
    new_source, missing = auto_import_python(source)
    assert "json" in missing
    # Existing ``import os`` should remain before the new ``import json``
    os_pos = new_source.index("import os")
    json_pos = new_source.index("import json")
    assert os_pos < json_pos
