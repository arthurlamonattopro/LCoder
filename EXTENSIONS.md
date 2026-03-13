# LCoder Extensions

This project supports a simple extension system inspired by VS Code. Extensions are Python modules loaded from the `extensions/` folder at startup. Each extension ships a manifest plus an optional entry file that registers commands and adds UI contributions.

## Folder Structure

Each extension is a folder inside `extensions/`:

- `extensions/your-extension/extension.json`
- `extensions/your-extension/main.py`

## Manifest (`extension.json`)

Minimum example:

```json
{
  "name": "hello-world",
  "publisher": "lcoder",
  "version": "0.0.1",
  "main": "main.py",
  "activationEvents": ["onStartupFinished"],
  "contributes": {
    "commands": [
      {
        "id": "helloWorld.showMessage",
        "title": "Hello World: Show Message"
      }
    ],
    "menus": [
      {
        "menu": "Extensions",
        "command": "helloWorld.showMessage",
        "label": "Hello World"
      }
    ]
  }
}
```

Supported fields:

- `name` (required)
- `publisher` (optional)
- `version` (optional)
- `main` (optional, defaults to `main.py`)
- `activationEvents` (optional)
- `contributes` (optional)

Activation events:

- `onStartupFinished`
- `*`
- `onCommand:<commandId>` (command activation is automatic when the menu item is clicked)

## Commands

Define commands in `contributes.commands` and register them in your `activate()` function:

```python
# extensions/your-extension/main.py

def activate(context):
    def do_something():
        context.window.show_info("Hello from my extension")

    context.commands.register_command("myext.doSomething", do_something)
```

Menu items call commands by id:

```json
{
  "menu": "Extensions",
  "command": "myext.doSomething",
  "label": "Do Something"
}
```

## Themes

You can contribute a theme file via `contributes.themes`:

```json
{
  "id": "ocean",
  "label": "Ocean",
  "path": "themes/ocean.json"
}
```

The theme JSON should follow the same structure as `core/themes.py` entries.

## Languages

You can contribute a language definition via `contributes.languages`:

```json
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
  "string_quotes": ["\"", "'"],
  "number_pattern": "\\b\\d+(\\.\\d+)?\\b"
}
```

## API Surface

Inside `activate(context)`, you have access to:

- `context.commands.register_command(id, callback)`
- `context.window.show_info|show_warning|show_error(message)`
- `context.window.add_menu_item(menu, label, command_id, shortcut=None)`
- `context.window.open_file(path)`
- `context.window.active_editor()`
- `context.workspace.root_path()`
- `context.workspace.open_folder(path)`
- `context.languages.register_language(language_id, config)`
- `context.themes.register_theme(theme_id, theme_dict, label=None)`

## Security Note

Extensions run arbitrary Python code. Only install extensions you trust.
