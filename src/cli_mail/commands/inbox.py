"""Inbox listing and refresh commands."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from cli_mail import ui

if TYPE_CHECKING:
    from cli_mail.app import App


def cmd_inbox(app: App, args: list[str]) -> None:
    if app.imap is None:
        ui.print_error("Not connected.")
        return
    page = 1
    if args:
        try:
            page = int(args[0])
        except ValueError:
            ui.print_error(f"Invalid page number: {args[0]}")
            return

    app.ctx.current_email = None

    with ui.console.status("[info]Fetching inbox...[/info]", spinner="dots"):
        offset = (page - 1) * app.ctx.page_size
        headers = app.imap.fetch_headers(
            folder=app.ctx.current_folder,
            limit=app.ctx.page_size,
            offset=offset,
        )
        total, _ = app.imap.folder_status(app.ctx.current_folder)

    app.ctx.inbox_cache = headers
    app.ctx.current_page = page
    total_pages = max(1, math.ceil(total / app.ctx.page_size))

    ui.print_inbox(headers, page, total_pages)


def cmd_refresh(app: App, args: list[str]) -> None:
    cmd_inbox(app, [str(app.ctx.current_page)])
    ui.print_success("Inbox refreshed")
