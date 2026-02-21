"""Account info and setup commands."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from rich.panel import Panel
from rich.table import Table

from cli_mail import ui
from cli_mail.auth import delete_password
from cli_mail.config import delete_account

if TYPE_CHECKING:
    from cli_mail.app import App


def cmd_account(app: App, args: list[str]) -> None:
    if app.ctx.account is None:
        ui.print_warning("No account configured.")
        return

    acct = app.ctx.account

    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold", width=14, justify="right")
    table.add_column()

    table.add_row("Account", acct.name)
    table.add_row("Email", acct.email)
    table.add_row("IMAP", f"{acct.imap_host}:{acct.imap_port}")
    table.add_row("SMTP", f"{acct.smtp_host}:{acct.smtp_port}")
    table.add_row("SSL", "Yes" if acct.use_ssl else "No")
    table.add_row("Status", "[success]Connected[/success]" if app.ctx.connected else "[error]Disconnected[/error]")

    ui.console.print(Panel(table, title="[bold]Account[/bold]", title_align="left", border_style="cyan"))
    ui.console.print()


def cmd_logout(app: App, args: list[str]) -> None:
    if app.ctx.account is None:
        ui.print_warning("No account to log out of.")
        return

    if not ui.prompt_confirm(f"Log out of {app.ctx.account.email}?"):
        return

    app._disconnect()
    delete_password(app.ctx.account.name)
    delete_account(app.ctx.account.name)
    ui.print_success("Logged out successfully.")
    ui.console.print()
    sys.exit(0)
