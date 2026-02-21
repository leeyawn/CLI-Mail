"""Folder listing and switching commands."""

from __future__ import annotations

from typing import TYPE_CHECKING

from cli_mail import ui

if TYPE_CHECKING:
    from cli_mail.app import App


def cmd_folders(app: App, args: list[str]) -> None:
    if app.imap is None:
        ui.print_error("Not connected.")
        return

    app.ctx.current_email = None

    with ui.console.status("[info]Loading folders...[/info]", spinner="dots"):
        folders = app.imap.list_folders()

    if not folders:
        ui.print_warning("No folders found.")
        return

    ui.print_folders(folders, current=app.ctx.current_folder)


def cmd_switch(app: App, args: list[str]) -> None:
    if app.imap is None:
        ui.print_error("Not connected.")
        return
    if not args:
        ui.print_error("Usage: /switch <folder>")
        return

    folder_name = " ".join(args)

    with ui.console.status("[info]Loading folders...[/info]", spinner="dots"):
        folders = app.imap.list_folders()

    folder_names = [f.name for f in folders]
    display_names = {f.display_name.lower(): f.name for f in folders}

    # Try matching in order: exact name, case-insensitive display name
    # (e.g. "sent" → "Sent Mail"), then uppercase (e.g. "inbox" → "INBOX").
    target = None
    if folder_name in folder_names:
        target = folder_name
    elif folder_name.lower() in display_names:
        target = display_names[folder_name.lower()]
    elif folder_name.upper() in folder_names:
        target = folder_name.upper()

    if target is None:
        ui.print_error(f'Folder "{folder_name}" not found.')
        ui.print_info("Available folders: " + ", ".join(f.display_name for f in folders))
        return

    app.ctx.current_folder = target
    app.ctx.current_page = 1
    app.ctx.current_email = None
    app.ctx.inbox_cache = []
    ui.print_success(f"Switched to {target}")

    from cli_mail.commands.inbox import cmd_inbox
    cmd_inbox(app, [])
