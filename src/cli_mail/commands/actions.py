"""Email action commands — star, delete, archive, mark read/unread."""

from __future__ import annotations

from typing import TYPE_CHECKING

from cli_mail import ui

if TYPE_CHECKING:
    from cli_mail.app import App


def _resolve_uid(app: App, args: list[str]) -> str | None:
    """Get the UID from args (inbox #) or the currently open email."""
    if args:
        try:
            idx = int(args[0]) - 1
        except ValueError:
            ui.print_error(f"Invalid number: {args[0]}")
            return None
        if idx < 0 or idx >= len(app.ctx.inbox_cache):
            ui.print_error(f"Email #{args[0]} not found.")
            return None
        return app.ctx.inbox_cache[idx].uid

    if app.ctx.current_email:
        return app.ctx.current_email.uid

    ui.print_error("No email selected. Specify a number or open an email first.")
    return None


def cmd_star(app: App, args: list[str]) -> None:
    if app.imap is None:
        ui.print_error("Not connected.")
        return
    uid = _resolve_uid(app, args)
    if uid is None:
        return

    is_flagged = False
    if app.ctx.current_email and app.ctx.current_email.uid == uid:
        is_flagged = app.ctx.current_email.is_flagged
    elif args:
        idx = int(args[0]) - 1
        is_flagged = app.ctx.inbox_cache[idx].is_flagged

    if is_flagged:
        app.imap.remove_flag(uid, "\\Flagged", app.ctx.current_folder)
        ui.print_success("Star removed")
    else:
        app.imap.set_flag(uid, "\\Flagged", app.ctx.current_folder)
        ui.print_success("Starred")


def cmd_delete(app: App, args: list[str]) -> None:
    if app.imap is None:
        ui.print_error("Not connected.")
        return
    uid = _resolve_uid(app, args)
    if uid is None:
        return

    if not ui.prompt_confirm("Delete this email?", default=False):
        ui.print_warning("Cancelled")
        return

    if app.imap.delete_email(uid, app.ctx.current_folder):
        ui.print_success("Email deleted")
        if app.ctx.current_email and app.ctx.current_email.uid == uid:
            app.ctx.current_email = None
    else:
        ui.print_error("Failed to delete email")


def cmd_archive(app: App, args: list[str]) -> None:
    if app.imap is None:
        ui.print_error("Not connected.")
        return
    uid = _resolve_uid(app, args)
    if uid is None:
        return

    archive_folders = ["[Gmail]/All Mail", "Archive", "Archives"]
    target = None

    with ui.console.status("[info]Finding archive folder...[/info]", spinner="dots"):
        folders = app.imap.list_folders()
        folder_names = {f.name.lower(): f.name for f in folders}

        for candidate in archive_folders:
            if candidate.lower() in folder_names:
                target = folder_names[candidate.lower()]
                break

    if target is None:
        ui.print_error("Could not find an archive folder.")
        return

    if app.imap.move_email(uid, target, app.ctx.current_folder):
        ui.print_success(f"Archived to {target}")
        if app.ctx.current_email and app.ctx.current_email.uid == uid:
            app.ctx.current_email = None
    else:
        ui.print_error("Failed to archive email")
