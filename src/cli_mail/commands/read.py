"""Read and display a single email."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from cli_mail import ui

if TYPE_CHECKING:
    from cli_mail.app import App


def cmd_read(app: App, args: list[str]) -> None:
    if not args:
        ui.print_error("Usage: /read <number>")
        return

    try:
        idx = int(args[0]) - 1
    except ValueError:
        ui.print_error(f"Invalid email number: {args[0]}")
        return

    if idx < 0 or idx >= len(app.ctx.inbox_cache):
        ui.print_error(f"Email #{args[0]} not found. Run /inbox first.")
        return

    header = app.ctx.inbox_cache[idx]

    with ui.console.status("[info]Loading email...[/info]", spinner="dots"):
        email = app.imap.fetch_email(header.uid, folder=app.ctx.current_folder)

    if email is None:
        ui.print_error("Failed to load email")
        return

    app.ctx.current_email = email
    ui.print_email(email)


def cmd_save_attachment(app: App, args: list[str]) -> None:
    if app.ctx.current_email is None:
        ui.print_error("No email open. Use /read <n> first.")
        return

    attachments = app.ctx.current_email.attachments
    if not attachments:
        ui.print_error("This email has no attachments.")
        return

    idx = 0
    if args:
        try:
            idx = int(args[0]) - 1
        except ValueError:
            ui.print_error(f"Invalid attachment number: {args[0]}")
            return

    if idx < 0 or idx >= len(attachments):
        ui.print_error(f"Attachment #{idx + 1} not found.")
        return

    att = attachments[idx]
    safe_name = Path(att.filename).name
    if not safe_name:
        safe_name = "unnamed_attachment"
    downloads = Path.home() / "Downloads"
    downloads.mkdir(parents=True, exist_ok=True)

    dest = downloads / safe_name
    counter = 1
    while dest.exists():
        stem = Path(safe_name).stem
        suffix = Path(safe_name).suffix
        dest = downloads / f"{stem}_{counter}{suffix}"
        counter += 1

    if dest.resolve().parent != downloads.resolve():
        ui.print_error("Invalid attachment filename.")
        return

    dest.write_bytes(att.payload)
    ui.print_success(f"Saved: {dest}")
