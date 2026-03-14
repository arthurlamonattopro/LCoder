"""Sample extension for LCoder."""


def activate(context):
    def show_message():
        if context.window:
            context.window.show_info("Hello from the Hello World extension.")
        else:
            context.log("[hello-world] Hello from the extension.\n")

    context.commands.register_command(
        "helloWorld.showMessage",
        show_message,
        title="Hello World: Show Message",
    )
    context.log("[hello-world] Activated.\n")


def deactivate():
    return None
