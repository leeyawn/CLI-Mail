"""Tests for command registry."""

from cli_mail.commands.registry import CommandRegistry


def _noop_handler(app, args):
    pass


class TestCommandRegistry:
    def test_register_and_get(self):
        reg = CommandRegistry()
        reg.register("inbox", _noop_handler, description="List emails")

        cmd = reg.get("inbox")
        assert cmd is not None
        assert cmd.name == "inbox"
        assert cmd.handler is _noop_handler
        assert cmd.description == "List emails"

    def test_get_by_alias(self):
        reg = CommandRegistry()
        reg.register("inbox", _noop_handler, aliases=["i", "ls"])

        assert reg.get("i") is not None
        assert reg.get("ls") is not None
        assert reg.get("i").name == "inbox"
        assert reg.get("ls").name == "inbox"

    def test_get_unknown_returns_none(self):
        reg = CommandRegistry()
        assert reg.get("nonexistent") is None

    def test_command_names_includes_aliases(self):
        reg = CommandRegistry()
        reg.register("inbox", _noop_handler, aliases=["i"])
        reg.register("quit", _noop_handler, aliases=["q", "exit"])

        names = reg.command_names
        assert "inbox" in names
        assert "i" in names
        assert "quit" in names
        assert "q" in names
        assert "exit" in names

    def test_commands_list(self):
        reg = CommandRegistry()
        reg.register("inbox", _noop_handler)
        reg.register("read", _noop_handler)

        cmds = reg.commands
        assert len(cmds) == 2
        cmd_names = {c.name for c in cmds}
        assert cmd_names == {"inbox", "read"}

    def test_multiple_commands_independent(self):
        reg = CommandRegistry()

        def handler_a(app, args):
            pass

        def handler_b(app, args):
            pass

        reg.register("a", handler_a)
        reg.register("b", handler_b)

        assert reg.get("a").handler is handler_a
        assert reg.get("b").handler is handler_b

    def test_alias_does_not_shadow_other_command(self):
        reg = CommandRegistry()
        reg.register("search", _noop_handler, aliases=["s"])
        reg.register("star", _noop_handler, aliases=["flag"])

        assert reg.get("s").name == "search"
        assert reg.get("flag").name == "star"
        assert reg.get("star").name == "star"
