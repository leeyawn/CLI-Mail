"""Account info, switching, and management commands."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from rich.panel import Panel
from rich.table import Table

from cli_mail import ui
from cli_mail.auth import delete_password
from cli_mail.config import (
    delete_account,
    get_account,
    get_default_account_name,
    list_accounts,
    set_default_account,
)
from cli_mail.models import AccountConfig

if TYPE_CHECKING:
    from cli_mail.app import App


def cmd_account_info(app: App, args: list[str]) -> None:
    if app.ctx.account is None:
        ui.print_warning("No account configured.")
        return

    acct = app.ctx.account
    default_name = get_default_account_name()
    total_accounts = len(list_accounts())

    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold", width=14, justify="right")
    table.add_column()

    table.add_row("Account", acct.name)
    table.add_row("Email", acct.email)
    table.add_row("IMAP", f"{acct.imap_host}:{acct.imap_port}")
    table.add_row("SMTP", f"{acct.smtp_host}:{acct.smtp_port}")
    table.add_row("SSL", "Yes" if acct.use_ssl else "No")
    table.add_row("Default", "Yes" if acct.name == default_name else "No")
    table.add_row("Status", "[success]Connected[/success]" if app.ctx.connected else "[error]Disconnected[/error]")

    if total_accounts > 1:
        table.add_row("Accounts", f"{total_accounts} configured — type /account list")

    ui.console.print(Panel(table, title="[bold]Account[/bold]", title_align="left", border_style="cyan"))
    ui.console.print()


def _load_all_accounts() -> list[AccountConfig]:
    """Load all AccountConfig objects in config order."""
    return [acct for name in list_accounts() if (acct := get_account(name)) is not None]


def cmd_account_list(app: App, args: list[str]) -> None:
    accounts = _load_all_accounts()
    if not accounts:
        ui.print_warning("No accounts configured.")
        return

    default_name = get_default_account_name()
    active_name = app.ctx.account.name if app.ctx.account else ""

    ui.print_accounts(accounts, active_name=active_name, default_name=default_name)


def cmd_account_switch(app: App, args: list[str]) -> None:
    app.ctx.current_email = None
    active_name = app.ctx.account.name if app.ctx.account else ""

    if args:
        target_name = args[0]
        if target_name == active_name:
            ui.print_info(f"Already on {target_name}.")
            ui.console.print()
            return
        app.switch_account(target_name)
        return

    accounts = _load_all_accounts()
    if not accounts:
        ui.print_warning("No accounts configured.")
        return

    default_name = get_default_account_name()
    ui.print_accounts(accounts, active_name=active_name, default_name=default_name)

    if len(accounts) < 2:
        return

    raw = ui.prompt_input("Switch to", default="")
    if not raw:
        ui.console.print()
        return

    try:
        idx = int(raw) - 1
        if 0 <= idx < len(accounts):
            target_name = accounts[idx].name
        else:
            ui.print_error("Invalid selection.")
            ui.console.print()
            return
    except ValueError:
        target_name = raw

    if target_name == active_name:
        ui.print_info(f"Already on {target_name}.")
        ui.console.print()
        return

    app.switch_account(target_name)


def cmd_account_add(app: App, args: list[str]) -> None:
    ui.console.print()
    account = app.setup_new_account()
    if account is None:
        return

    if ui.prompt_confirm(f"Switch to {account.name} now?", default=False):
        app.switch_account(account.name)
    else:
        ui.console.print()


def cmd_account_default(app: App, args: list[str]) -> None:
    if not args:
        current = get_default_account_name()
        if current:
            ui.print_info(f"Current default: {current}")
        ui.print_info("Usage: /account default <account-name>")
        return

    name = args[0]
    if set_default_account(name):
        ui.print_success(f"Default account set to {name}.")
    else:
        ui.print_error(f'Account "{name}" not found.')
        names = list_accounts()
        if names:
            ui.print_info(f"Available: {', '.join(names)}")


def cmd_account_logout(app: App, args: list[str]) -> None:
    if app.ctx.account is None:
        ui.print_warning("No account to log out of.")
        return

    if not ui.prompt_confirm(f"Log out of {app.ctx.account.email}?"):
        return

    account_name = app.ctx.account.name
    app._disconnect()
    delete_password(account_name)
    delete_account(account_name)
    app._passwords.pop(account_name, None)
    ui.print_success("Logged out successfully.")

    remaining = list_accounts()
    if not remaining:
        ui.console.print()
        sys.exit(0)

    app.switch_account(remaining[0])


_SUBCOMMANDS = frozenset({"list", "switch", "add", "default", "logout"})


def cmd_account_dispatch(app: App, args: list[str]) -> None:
    if not args:
        cmd_account_info(app, args)
        return

    sub = args[0].lower()
    if sub in _SUBCOMMANDS:
        globals()[f"cmd_account_{sub}"](app, args[1:])
    else:
        ui.print_error(f"Unknown subcommand: {sub}")
        ui.print_info("Subcommands: list, switch, add, default, logout")
