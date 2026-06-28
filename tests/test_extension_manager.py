"""Tests for core.extensions.ExtensionManager.

These tests do NOT require a running QApplication — they cover the
manifest discovery, contribution registration and command dispatch logic.
"""
import json

from core.extensions import ExtensionManager


def _make_extension(root, name, manifest, main_code=None):
    ext_dir = root / "extensions" / name
    ext_dir.mkdir(parents=True)
    (ext_dir / "extension.json").write_text(json.dumps(manifest))
    if main_code is not None:
        (ext_dir / "main.py").write_text(main_code)
    return ext_dir


def test_discover_extensions_finds_manifest(tmp_path):
    _make_extension(
        tmp_path,
        "hello",
        {
            "name": "hello",
            "publisher": "lcoder",
            "version": "0.0.1",
            "main": "main.py",
            "activationEvents": ["onStartupFinished"],
            "contributes": {
                "commands": [{"id": "hello.show", "title": "Hello: Show"}],
                "menus": [
                    {
                        "menu": "Extensions",
                        "command": "hello.show",
                        "label": "Hello",
                    }
                ],
            },
        },
        main_code="def activate(context):\n    pass\n",
    )
    em = ExtensionManager(config_manager=None, app_root=str(tmp_path))
    em.discover_extensions()

    assert "lcoder.hello" in em._extensions
    ext = em._extensions["lcoder.hello"]
    assert ext.manifest["name"] == "hello"
    assert ext.activated is False


def test_discover_ignores_dirs_without_manifest(tmp_path):
    no_manifest_dir = tmp_path / "extensions" / "no-manifest"
    no_manifest_dir.mkdir(parents=True)
    (no_manifest_dir / "readme.txt").write_text("not an extension")

    em = ExtensionManager(config_manager=None, app_root=str(tmp_path))
    em.discover_extensions()
    assert em._extensions == {}


def test_load_contributions_registers_commands_and_menus(tmp_path):
    _make_extension(
        tmp_path,
        "hello",
        {
            "name": "hello",
            "publisher": "lcoder",
            "main": "main.py",
            "activationEvents": ["onStartupFinished"],
            "contributes": {
                "commands": [
                    {"id": "hello.show", "title": "Hello: Show"},
                    {"id": "hello.run", "title": "Hello: Run"},
                ],
                "menus": [
                    {"menu": "Extensions", "command": "hello.show", "label": "Show"},
                ],
            },
        },
        main_code="def activate(context):\n    pass\n",
    )
    em = ExtensionManager(config_manager=None, app_root=str(tmp_path))
    em.discover_extensions()
    em.load_contributions()

    assert em.commands.get_title("hello.show") == "Hello: Show"
    assert em.commands.get_title("hello.run") == "Hello: Run"
    assert len(em._menu_contributions) == 1
    assert em._menu_contributions[0]["command"] == "hello.show"


def test_activate_extension_runs_activate_function(tmp_path):
    main_code = (
        "def activate(context):\n"
        "    context.commands.register_command('hello.show', lambda: 'ok')\n"
    )
    _make_extension(
        tmp_path,
        "hello",
        {
            "name": "hello",
            "publisher": "lcoder",
            "main": "main.py",
            "activationEvents": ["onStartupFinished"],
            "contributes": {"commands": [{"id": "hello.show", "title": "Hello"}]},
        },
        main_code=main_code,
    )
    logs = []
    em = ExtensionManager(config_manager=None, app_root=str(tmp_path))
    em.set_log_callback(logs.append)
    em.discover_extensions()
    em.load_contributions()

    ok = em.activate_extension("lcoder.hello")
    assert ok is True
    assert em._extensions["lcoder.hello"].activated is True

    # Command should now be registered and dispatchable
    result = em.commands.execute_command("hello.show")
    assert result == "ok"


def test_activate_unknown_extension_returns_false(tmp_path):
    em = ExtensionManager(config_manager=None, app_root=str(tmp_path))
    em.set_log_callback(lambda _: None)
    assert em.activate_extension("does.not.exist") is False


def test_execute_command_lazily_activates_extension(tmp_path):
    """Calling an unregistered command from a known extension should activate it."""
    main_code = (
        "called = {'count': 0}\n"
        "def _handler():\n"
        "    called['count'] += 1\n"
        "    return called['count']\n"
        "def activate(context):\n"
        "    context.commands.register_command('hello.go', _handler)\n"
    )
    _make_extension(
        tmp_path,
        "hello",
        {
            "name": "hello",
            "publisher": "lcoder",
            "main": "main.py",
            "activationEvents": ["onCommand:hello.go"],
            "contributes": {"commands": [{"id": "hello.go", "title": "Go"}]},
        },
        main_code=main_code,
    )
    em = ExtensionManager(config_manager=None, app_root=str(tmp_path))
    em.set_log_callback(lambda _: None)
    em.discover_extensions()
    em.load_contributions()

    # Before invocation, the extension is not activated.
    assert em._extensions["lcoder.hello"].activated is False

    # First call triggers activation, then runs the handler.
    result = em.commands.execute_command("hello.go")
    assert result == 1
    assert em._extensions["lcoder.hello"].activated is True

    # Second call uses the already-registered callback.
    assert em.commands.execute_command("hello.go") == 2


def test_register_language_contribution(tmp_path):
    _make_extension(
        tmp_path,
        "toml-ext",
        {
            "name": "toml-ext",
            "publisher": "lcoder",
            "main": "main.py",
            "activationEvents": ["onStartupFinished"],
            "contributes": {
                "languages": [
                    {
                        "id": "toml",
                        "name": "TOML",
                        "extensions": [".toml"],
                        "executable": "",
                        "run_args": ["{file}"],
                        "repl_args": [],
                        "keywords": [],
                        "functions": [],
                        "comment_prefix": "#",
                        "string_quotes": ['"', "'"],
                        "number_pattern": r"\b\d+(\.\d+)?\b",
                    }
                ]
            },
        },
        main_code="def activate(context):\n    pass\n",
    )

    # Fake config_manager so register_language can probe for the language entry.
    class FakeConfig:
        def __init__(self):
            self.data = {"languages": {}}

        def get(self, *keys):
            v = self.data
            for k in keys:
                if not isinstance(v, dict) or k not in v:
                    return None
                v = v[k]
            return v

        def set(self, value, *keys):
            d = self.data
            for k in keys[:-1]:
                d = d.setdefault(k, {})
            d[keys[-1]] = value

    em = ExtensionManager(config_manager=FakeConfig(), app_root=str(tmp_path))
    em.set_log_callback(lambda _: None)
    em.discover_extensions()
    em.load_contributions()

    from core.languages import LANGUAGES

    assert "toml" in LANGUAGES
    assert LANGUAGES["toml"]["name"] == "TOML"
    assert ".toml" in LANGUAGES["toml"]["extensions"]
