"""Compose, reply, and forward commands."""

from __future__ import annotations

from typing import TYPE_CHECKING

from cli_mail import ui
from cli_mail.sender import SMTPSender

if TYPE_CHECKING:
    from cli_mail.app import App


def _collect_body() -> str | None:
    """Collect multi-line message body. Returns None if cancelled."""
    ui.print_compose_help()
    lines: list[str] = []
    try:
        while True:
            line = input()
            if line.strip() == ":send":
                return "\n".join(lines)
            if line.strip() == ":cancel":
                return None
            lines.append(line)
    except (EOFError, KeyboardInterrupt):
        return None


def cmd_compose(app: App, args: list[str]) -> None:
    if app.ctx.account is None:
        ui.print_error("No account configured.")
        return
    to = ui.prompt_input("To")
    if not to:
        ui.print_error("Cancelled — no recipient.")
        return

    subject = ui.prompt_input("Subject")
    cc = ui.prompt_input("Cc")

    ui.console.print()
    body = _collect_body()
    if body is None:
        ui.print_warning("Message discarded.")
        return

    recipients = [addr.strip() for addr in to.split(",") if addr.strip()]
    cc_list = [addr.strip() for addr in cc.split(",") if addr.strip()] if cc else None

    if not recipients:
        ui.print_error("No valid recipients.")
        return

    try:
        with ui.console.status("[info]Sending...[/info]", spinner="dots"):
            sender = SMTPSender(app.ctx.account)
            sender.send(
                password=app.password,
                to=recipients,
                subject=subject,
                body=body,
                cc=cc_list,
            )
        ui.print_success("Email sent!")
    except Exception as e:
        ui.print_error(f"Failed to send: {e}")


def cmd_reply(app: App, args: list[str]) -> None:
    if app.ctx.account is None:
        ui.print_error("No account configured.")
        return
    if app.ctx.current_email is None:
        ui.print_error("No email open. Use /read <n> first.")
        return

    original = app.ctx.current_email
    ui.print_info(f"Replying to: {original.sender}")
    ui.console.print()

    body = _collect_body()
    if body is None:
        ui.print_warning("Reply discarded.")
        return

    try:
        with ui.console.status("[info]Sending reply...[/info]", spinner="dots"):
            sender = SMTPSender(app.ctx.account)
            sender.reply(password=app.password, original=original, body=body)
        ui.print_success("Reply sent!")
    except Exception as e:
        ui.print_error(f"Failed to send reply: {e}")


def cmd_forward(app: App, args: list[str]) -> None:
    if app.ctx.account is None:
        ui.print_error("No account configured.")
        return
    if app.ctx.current_email is None:
        ui.print_error("No email open. Use /read <n> first.")
        return

    to = args[0] if args else ui.prompt_input("Forward to")
    if not to:
        ui.print_error("Cancelled — no recipient.")
        return

    ui.print_info("Add a message (optional):")
    ui.console.print()
    body = _collect_body()
    if body is None:
        ui.print_warning("Forward discarded.")
        return

    try:
        with ui.console.status("[info]Forwarding...[/info]", spinner="dots"):
            sender = SMTPSender(app.ctx.account)
            sender.forward(
                password=app.password,
                original=app.ctx.current_email,
                to=[addr.strip() for addr in to.split(",")],
                body=body,
            )
        ui.print_success("Email forwarded!")
    except Exception as e:
        ui.print_error(f"Failed to forward: {e}")
