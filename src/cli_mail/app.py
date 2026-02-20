"""Main application — REPL loop, account setup, and command dispatch."""

from __future__ import annotations

import sys

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import FileHistory
from prompt_toolkit.formatted_text import HTML

from cli_mail import ui
from cli_mail.auth import get_password, store_password
from cli_mail.client import IMAPClient
from cli_mail.commands.account import cmd_account
from cli_mail.commands.actions import cmd_archive, cmd_delete, cmd_star
from cli_mail.commands.compose import cmd_compose, cmd_forward, cmd_reply
from cli_mail.commands.folders import cmd_folders, cmd_switch
from cli_mail.commands.inbox import cmd_inbox, cmd_refresh
from cli_mail.commands.read import cmd_read, cmd_save_attachment
from cli_mail.commands.registry import CommandRegistry
from cli_mail.commands.search import cmd_search
from cli_mail.config import (
    CONFIG_DIR,
    get_account,
    guess_provider,
    list_accounts,
    save_account,
)
from cli_mail.models import AccountConfig, AppContext


def _prompt_port(label: str, default: int = 993) -> int:
    while True:
        raw = ui.prompt_input(label, default=str(default))
        try:
            port = int(raw)
            if 1 <= port <= 65535:
                return port
            ui.print_error("Port must be between 1 and 65535.")
        except ValueError:
            ui.print_error(f'"{raw}" is not a valid port number.')


class App:
    def __init__(self) -> None:
        self.ctx = AppContext()
        self.imap: IMAPClient | None = None
        self.password: str = ""
        self.registry = CommandRegistry()
        self._register_commands()

        history_path = CONFIG_DIR / "history"
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self.session: PromptSession = PromptSession(
            history=FileHistory(str(history_path)),
            completer=WordCompleter(
                ["/" + n for n in self.registry.command_names],
                sentence=True,
            ),
        )

    def _register_commands(self) -> None:
        r = self.registry
        r.register("inbox", cmd_inbox, aliases=["i", "ls"], description="List emails")
        r.register("read", cmd_read, aliases=["r", "open"], description="Read an email")
        r.register("reply", cmd_reply, aliases=["re"], description="Reply to current email")
        r.register("compose", cmd_compose, aliases=["c", "new"], description="Compose new email")
        r.register("forward", cmd_forward, aliases=["fwd"], description="Forward current email")
        r.register("search", cmd_search, aliases=["s", "find"], description="Search emails")
        r.register("folders", cmd_folders, aliases=["f"], description="List folders")
        r.register("switch", cmd_switch, aliases=["sw", "cd"], description="Switch folder")
        r.register("star", cmd_star, aliases=["flag"], description="Toggle star")
        r.register("delete", cmd_delete, aliases=["del", "rm"], description="Delete email")
        r.register("archive", cmd_archive, aliases=["ar"], description="Archive email")
        r.register("save", cmd_save_attachment, description="Save attachment")
        r.register("account", cmd_account, aliases=["acc", "whoami"], description="Account info")
        r.register("refresh", cmd_refresh, aliases=["ref"], description="Refresh inbox")
        r.register("help", lambda app, args: app._cmd_help(args), aliases=["h", "?"], description="Show help")
        r.register("quit", lambda app, args: app._cmd_quit(args), aliases=["q", "exit"], description="Exit")

    def _cmd_help(self, args: list[str]) -> None:
        ui.print_help()

    def _cmd_quit(self, args: list[str]) -> None:
        self._disconnect()
        ui.console.print()
        ui.print_info("Goodbye!")
        ui.console.print()
        sys.exit(0)

    def _disconnect(self) -> None:
        if self.imap:
            self.imap.disconnect()
            self.ctx.connected = False

    def _setup_account(self) -> bool:
        """Interactive first-run account setup. Returns True on success."""
        ui.console.print("  [bold]No accounts configured. Let's set one up.[/bold]")
        ui.console.print()

        email_addr = ui.prompt_input("Email address")
        if not email_addr or "@" not in email_addr:
            ui.print_error("Invalid email address.")
            return False

        defaults = guess_provider(email_addr)
        imap_host = ui.prompt_input("IMAP server", default=str(defaults.get("imap_host", "")))
        if not imap_host:
            ui.print_error("IMAP server is required.")
            return False

        imap_port = _prompt_port("IMAP port", default=defaults.get("imap_port", 993))
        smtp_host = ui.prompt_input("SMTP server", default=str(defaults.get("smtp_host", imap_host.replace("imap", "smtp", 1))))
        smtp_port = _prompt_port("SMTP port", default=defaults.get("smtp_port", 587))

        password = ui.prompt_password()
        if not password:
            ui.print_error("Password is required.")
            return False

        account = AccountConfig(
            email=email_addr,
            imap_host=imap_host,
            imap_port=imap_port,
            smtp_host=smtp_host,
            smtp_port=smtp_port,
        )

        ui.console.print()
        with ui.console.status("[info]Connecting...[/info]", spinner="dots"):
            try:
                test_client = IMAPClient(account)
                test_client.connect(password)
                test_client.disconnect()
            except Exception as e:
                ui.print_error(f"Connection failed: {e}")
                return False

        ui.print_success("Connected successfully!")

        save_account(account)
        store_password(account.name, password)
        ui.print_success("Account saved.")
        ui.console.print()

        self.ctx.account = account
        self.password = password
        return True

    def _connect(self) -> bool:
        """Connect to the IMAP server. Returns True on success."""
        account = self.ctx.account
        if account is None:
            return False

        password = self.password
        if not password:
            password = get_password(account.name) or ""
        if not password:
            password = ui.prompt_password()
        if not password:
            ui.print_error("Password required.")
            return False

        self.password = password

        self._disconnect()
        with ui.console.status("[info]Connecting...[/info]", spinner="dots"):
            try:
                self.imap = IMAPClient(account)
                self.imap.connect(password)
                self.ctx.connected = True
            except Exception as e:
                self.ctx.connected = False
                ui.print_error(f"Connection failed: {e}")
                return False

        return True

    def _get_prompt(self) -> HTML:
        folder = self.ctx.current_folder
        if self.ctx.current_email:
            subject = self.ctx.current_email.subject
            if len(subject) > 30:
                subject = subject[:27] + "..."
            return HTML(f"<b><style fg='cyan'>{folder}</style></b> <style fg='ansibrightblack'>({subject})</style> <b>&gt;</b> ")
        return HTML(f"<b><style fg='cyan'>{folder}</style></b> <b>&gt;</b> ")

    def _dispatch(self, user_input: str) -> None:
        """Parse and dispatch a user command."""
        if user_input.startswith("/"):
            parts = user_input[1:].split(maxsplit=1)
            cmd_name = parts[0].lower()
            args = parts[1].split() if len(parts) > 1 else []

            command = self.registry.get(cmd_name)
            if command:
                try:
                    command.handler(self, args)
                except ConnectionError:
                    ui.print_error("Lost connection. Reconnecting...")
                    if self._connect():
                        command.handler(self, args)
                except Exception as e:
                    ui.print_error(f"Error: {e}")
            else:
                ui.print_error(f"Unknown command: /{cmd_name}")
                ui.print_info("Type /help for a list of commands.")
        else:
            if user_input.isdigit():
                self._dispatch(f"/read {user_input}")
            else:
                self._dispatch(f"/search {user_input}")

    def run(self) -> None:
        """Main entry point — setup, connect, REPL."""
        ui.print_banner()

        accounts = list_accounts()
        if not accounts:
            if not self._setup_account():
                return
        else:
            self.ctx.account = get_account()
            if self.ctx.account is None:
                ui.print_error("Could not load account from config. Re-running setup.")
                ui.console.print()
                if not self._setup_account():
                    return

        if not self._connect():
            return

        ui.print_status_bar(self.ctx)

        try:
            total, unread = self.imap.folder_status("INBOX")
            if unread > 0:
                ui.print_info(f"{unread} unread message{'s' if unread != 1 else ''} in Inbox ({total} total)")
            else:
                ui.print_info(f"{total} messages in Inbox")
        except Exception:
            ui.print_info("Connected. Type /inbox to list messages.")
        ui.console.print()

        while True:
            try:
                user_input = self.session.prompt(self._get_prompt).strip()
                if not user_input:
                    continue
                self._dispatch(user_input)
            except KeyboardInterrupt:
                continue
            except EOFError:
                self._cmd_quit([])


def main() -> None:
    try:
        app = App()
        app.run()
    except KeyboardInterrupt:
        ui.console.print()
        ui.print_info("Goodbye!")
